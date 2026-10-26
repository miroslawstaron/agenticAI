"""One scheduler, durable events, workflow routing and autonomous mailboxes."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections import defaultdict

from .models import Agent, Link, Network, Provider, Tool, identifier
from .security import redact, register_references
from .store import Store
from .tools import ToolRunner, substitute
from .transport import Transport


class LimitReached(RuntimeError):
    pass


def function(
    name: str, description: str, properties: dict, required: list[str] = ()
) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(required),
                "additionalProperties": False,
            },
        },
    }


ORCHESTRATION = [
    function(
        "send_message",
        "Send a message to a connected agent.",
        {"target": {"type": "string"}, "message": {"type": "string"}},
        ["target", "message"],
    ),
    function(
        "broadcast",
        "Send a message to all outgoing neighbors.",
        {"message": {"type": "string"}},
        ["message"],
    ),
    function(
        "publish",
        "Publish to a topic subscribed by connected agents.",
        {"topic": {"type": "string"}, "message": {"type": "string"}},
        ["topic", "message"],
    ),
    function(
        "spawn_agent",
        "Create a child using your provider/model and a subset of your tools, and optionally delegate a task.",
        {
            "name": {"type": "string"},
            "role": {"type": "string"},
            "tools": {"type": "array", "items": {"type": "string"}},
            "task": {"type": "string"},
            "can_orchestrate": {"type": "boolean"},
        },
        ["name", "role"],
    ),
    function(
        "delegate",
        "Delegate a task to a connected agent and receive its result asynchronously.",
        {"target": {"type": "string"}, "task": {"type": "string"}},
        ["target", "task"],
    ),
    function(
        "connect_agents",
        "Add or remove one of your outgoing communication links.",
        {"target": {"type": "string"}, "remove": {"type": "boolean"}},
        ["target"],
    ),
    function(
        "subscribe",
        "Subscribe yourself to a topic or unsubscribe.",
        {"topic": {"type": "string"}, "remove": {"type": "boolean"}},
        ["topic"],
    ),
]


class Run:
    def __init__(
        self, manager: "Manager", id: str, network: Network, prompt: str, snapshot: dict
    ):
        self.manager, self.store, self.id = manager, manager.store, id
        self.network = network.model_copy(deep=True)
        self.prompt = prompt
        self.providers = {
            p["id"]: Provider.model_validate(p) for p in snapshot["providers"]
        }
        self.tools = {t["id"]: Tool.model_validate(t) for t in snapshot["tools"]}
        self.agents = {a.id: a for a in self.network.agents}
        self.messages: dict[str, list[dict]] = defaultdict(list)
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.visits: dict[str, int] = defaultdict(int)
        self.gate = asyncio.Event()
        self.gate.set()
        self.wake = asyncio.Event()
        self.inbox: list[dict] = []
        self.human: dict[str, asyncio.Future] = {}
        self.join_buffers: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.delegations: dict[str, str] = {}
        self.calls, self.steps, self.active = 0, 0, 0.0
        self.model_slots = asyncio.Semaphore(network.limits.concurrency)
        self.tool_runner = ToolRunner(self.store.root, network.limits.tool_concurrency)
        self.status = "queued"
        self.workspace = self.store.root / "runs" / id
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.task: asyncio.Task | None = None

    def event(self, kind: str, **body):
        self.store.event(self.id, kind, redact(body))

    def state(self, status: str, error: str = ""):
        self.status = status
        self.store.update_run(self.id, status, redact(error))
        self.event("status", status=status, error=error)

    def append(self, agent: str, message: dict):
        message = redact(message)
        self.messages[agent].append(message)
        self.store.message(self.id, agent, message)
        if message.get("role") != "system":
            self.event("message", agent_id=agent, message=message)

    def enqueue(self, target: str, message: str, source: str = "user"):
        if target not in self.agents:
            raise ValueError(f"Unknown agent: {target}")
        if not isinstance(message, str) or len(message) > 1000000:
            raise ValueError(
                "Messages must be strings of at most one million characters"
            )
        self.inbox.append({"target": target, "source": source, "message": message})
        if (
            len(self.inbox)
            > self.network.limits.max_steps * self.network.limits.max_agents
        ):
            raise LimitReached("Message queue limit reached")
        self.event("delivery", source=source, target=target, message=message)
        self.wake.set()

    def neighbors(self, agent_id: str) -> set[str]:
        return {link.target for link in self.network.links if link.source == agent_id}

    async def execute(self):
        try:
            self.state("running")
            entries = self.network.entry_agents or [
                a.id
                for a in self.network.agents
                if not any(link.target == a.id for link in self.network.links)
            ]
            if not entries:
                raise ValueError("Choose at least one entry agent for a cyclic network")
            for target in entries:
                self.enqueue(target, self.prompt)
            while self.inbox:
                await self.gate.wait()
                if self.status != "running":
                    self.state("running")
                batch, self.inbox = self.inbox, []
                grouped: dict[str, list[dict]] = defaultdict(list)
                for item in batch:
                    grouped[item["target"]].append(item)
                budget = self.network.limits.active_seconds - self.active
                if budget <= 0:
                    raise LimitReached("Active execution time limit reached")
                # Human-only waves do not count as active time. Mixed waves pause
                # accounting for each interval where all remaining work is human input.
                tasks = [
                    asyncio.create_task(self._activation(target, items))
                    for target, items in grouped.items()
                ]
                self._wave_tasks = tasks
                remaining = set(tasks)
                last = time.monotonic()
                try:
                    while remaining:
                        done, pending = await asyncio.wait(
                            remaining, timeout=0.05, return_when=asyncio.FIRST_COMPLETED
                        )
                        now = time.monotonic()
                        waiting_only = all(
                            getattr(t, "_human_wait", False)
                            or getattr(t, "_paused_wait", False)
                            for t in remaining
                        )
                        if not waiting_only:
                            self.active += now - last
                        elif self.status == "running" and self.human:
                            self.state("waiting")
                        last = now
                        if self.active >= self.network.limits.active_seconds:
                            raise LimitReached("Active execution time limit reached")
                        for task in done:
                            task.result()
                        remaining = pending
                finally:
                    for task in remaining:
                        task.cancel()
                    await asyncio.gather(*remaining, return_exceptions=True)
            unfinished = {
                target: dict(parts)
                for target, parts in self.join_buffers.items()
                if any(parts.values())
            }
            if unfinished:
                raise ValueError(
                    "Join is missing input from a predecessor. Check branch conditions or loop structure."
                )
            if self.delegations:
                raise ValueError(
                    "A delegated task could not complete. Check target visit limits and routing."
                )
            self.event(
                "summary",
                calls=self.calls,
                steps=self.steps,
                active_seconds=self.active,
                network=self.network.model_dump(),
            )
            self.state("completed")
        except asyncio.CancelledError:
            self.state("cancelled")
        except LimitReached as exc:
            self.state("limited", str(exc))
        except Exception as exc:
            self.event("error", error=str(exc))
            self.state("failed", str(exc))
        finally:
            self.event("run_snapshot", network=self.network.model_dump())

    async def _activation(self, target: str, items: list[dict]):
        async with self.locks[target]:
            agent = self.agents[target]
            if self.visits[target] >= agent.max_visits:
                self.event("visit_limit", agent_id=target, max_visits=agent.max_visits)
                return
            if agent.kind == "join":
                buffer = self.join_buffers[target]
                for item in items:
                    if item["source"] != "__join_flush__":
                        buffer[item["source"]].append(item["message"])
                expected = {
                    link.source for link in self.network.links if link.target == target
                }
                if not expected.issubset(
                    {key for key, values in buffer.items() if values}
                ):
                    return
                items = [
                    {"source": source, "message": buffer[source].pop(0)}
                    for source in sorted(expected)
                ]
            self.steps += 1
            if self.steps > self.network.limits.max_steps:
                raise LimitReached("Execution step limit reached")
            self.visits[target] += 1
            text = "\n\n".join(
                item["message"]
                if len(items) == 1
                else f"From {item['source']}:\n{item['message']}"
                for item in items
            )
            self.event(
                "agent_started",
                agent_id=target,
                name=agent.name,
                visit=self.visits[target],
            )
            if agent.kind == "human":
                future = asyncio.get_running_loop().create_future()
                self.human[target] = future
                self.event("human_input", agent_id=target, prompt=text)
                current = asyncio.current_task()
                current._human_wait = True
                try:
                    response = await future
                finally:
                    current._human_wait = False
                    self.human.pop(target, None)
                self.append(target, {"role": "user", "content": text})
                self.append(target, {"role": "assistant", "content": response})
            elif agent.kind == "tool":
                tool = self.tools[agent.tool_id]
                args = {
                    k: substitute(v, {"message": text}) if isinstance(v, str) else v
                    for k, v in agent.tool_arguments.items()
                }
                result = await self._tool(agent, tool, args)
                response = json.dumps(result, ensure_ascii=False)
                self.append(target, {"role": "assistant", "content": response})
                if not result["ok"]:
                    self.event("tool_failure", agent_id=target, result=result)
                    raise RuntimeError(
                        f"{tool.name}: {result['error'] or result['stderr'] or 'Tool step failed'}"
                    )
            elif agent.kind == "join":
                response = text
                self.append(target, {"role": "assistant", "content": response})
            else:
                if not self.messages[target]:
                    self.append(target, {"role": "system", "content": agent.role})
                self.append(target, {"role": "user", "content": text})
                response = await self._agent_loop(agent)
            self.event("agent_completed", agent_id=target, content=response)
            if agent.kind == "join":
                expected = {
                    link.source for link in self.network.links if link.target == target
                }
                if all(self.join_buffers[target][source] for source in expected):
                    self.inbox.append(
                        {"target": target, "source": "__join_flush__", "message": ""}
                    )
            if target in self.delegations:
                parent = self.delegations.pop(target)
                self.enqueue(
                    parent, f"Delegated result from {agent.name}:\n{response}", target
                )
            if self.network.mode == "workflow":
                for link in list(self.network.links):
                    if link.source == target and link.matches(response):
                        values = {"message": response, "task": self.prompt}
                        message = re.sub(
                            r"\{(message|task)\}",
                            lambda match: values[match.group(1)],
                            link.template,
                        )
                        self.enqueue(link.target, message, target)

    async def _agent_loop(self, agent: Agent) -> str:
        provider = self.providers[agent.provider_id]
        definitions = []
        mapping = {}
        if provider.supports_tools or provider.kind == "demo":
            for index, tool_id in enumerate(agent.tools):
                tool = self.tools[tool_id]
                name = f"tool_{index}_{tool_id}"
                import re

                name = re.sub(r"[^A-Za-z0-9_-]", "_", name)[:64]
                mapping[name] = tool
                definitions.append(
                    {
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": tool.description or tool.name,
                            "parameters": tool.input_schema,
                        },
                    }
                )
            if self.network.mode == "autonomous" and agent.can_orchestrate:
                definitions += ORCHESTRATION
        while True:
            task = asyncio.current_task()
            task._paused_wait = not self.gate.is_set()
            try:
                await self.gate.wait()
            finally:
                task._paused_wait = False
            if self.calls >= self.network.limits.max_calls:
                raise LimitReached("Model call limit reached")
            self.calls += 1
            start = time.perf_counter()
            async with self.model_slots, self.manager.global_slots:
                result = await self.manager.transport.complete(
                    provider, agent, self.messages[agent.id], definitions
                )
            message = result["message"]
            self.append(agent.id, message)
            self.event(
                "model_call",
                agent_id=agent.id,
                duration=time.perf_counter() - start,
                usage=result.get("usage", {}),
                context_policy="conservative UTF-8 byte budget",
            )
            calls = message.get("tool_calls") or []
            if not calls:
                return message.get("content") or ""
            if not definitions:
                raise ValueError("Model returned tool calls without enabled tools")
            seen = set()
            for call in calls:
                call_id = call.get("id")
                if not call_id or call_id in seen:
                    raise ValueError(
                        "Model returned missing or duplicate tool call ids"
                    )
                seen.add(call_id)
                try:
                    name = call["function"]["name"]
                    args = json.loads(call["function"]["arguments"])
                    if not isinstance(args, dict):
                        raise ValueError("Tool arguments must be an object")
                    if name in mapping:
                        output = await self._tool(agent, mapping[name], args)
                    elif (
                        name in {d["function"]["name"] for d in ORCHESTRATION}
                        and agent.can_orchestrate
                        and self.network.mode == "autonomous"
                    ):
                        from jsonschema import validate

                        definition = next(
                            d for d in ORCHESTRATION if d["function"]["name"] == name
                        )
                        validate(args, definition["function"]["parameters"])
                        output = self._orchestrate(agent, name, args)
                    else:
                        raise ValueError("Tool is not enabled for this agent")
                except LimitReached:
                    raise
                except Exception as exc:
                    output = {"ok": False, "error": str(exc)}
                    self.event("tool_error", agent_id=agent.id, error=str(exc))
                self.append(
                    agent.id,
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(redact(output), ensure_ascii=False),
                    },
                )

    async def _tool(self, agent: Agent, tool: Tool, args: dict) -> dict:
        work = self.workspace / agent.id / identifier()
        self.event("tool_started", agent_id=agent.id, tool_id=tool.id, arguments=args)
        result = await self.tool_runner.execute(tool, args, work)
        self.event(
            "tool_completed",
            agent_id=agent.id,
            tool_id=tool.id,
            result=result.model_dump(),
        )
        return result.model_dump()

    def _orchestrate(self, agent: Agent, name: str, args: dict) -> dict:
        target = args.get("target")
        if name in ("send_message", "delegate") and target not in self.neighbors(
            agent.id
        ):
            raise ValueError("Connect an outgoing link to the target first")
        if name == "send_message":
            self.enqueue(target, args["message"], agent.id)
        elif name == "broadcast":
            for target in self.neighbors(agent.id):
                self.enqueue(target, args["message"], agent.id)
        elif name == "publish":
            for target in self.neighbors(agent.id):
                if args["topic"] in self.agents[target].topics:
                    self.enqueue(target, args["message"], agent.id)
        elif name == "delegate":
            if target in self.delegations or target == agent.id:
                raise ValueError(
                    "Target already has a delegation or refers to the sender"
                )
            self.delegations[target] = agent.id
            self.enqueue(target, args["task"], agent.id)
        elif name == "spawn_agent":
            if len(self.agents) >= self.network.limits.max_agents:
                raise LimitReached("Agent limit reached")
            tool_ids = args.get("tools", [])
            if not set(tool_ids).issubset(set(agent.tools)):
                raise ValueError("Child tools must be a subset of parent tools")
            child = agent.model_copy(
                update={
                    "id": identifier(),
                    "name": args["name"],
                    "role": args["role"],
                    "tools": tool_ids,
                    "can_orchestrate": bool(args.get("can_orchestrate", False)),
                    "x": agent.x + 320,
                    "y": agent.y + len(self.agents) * 90,
                },
                deep=True,
            )
            self.agents[child.id] = child
            self.network.agents.append(child)
            self.network.links.extend(
                [
                    Link(source=agent.id, target=child.id),
                    Link(source=child.id, target=agent.id),
                ]
            )
            if args.get("task"):
                self.delegations[child.id] = agent.id
                self.enqueue(child.id, args["task"], agent.id)
            self.event(
                "network_changed", action=name, network=self.network.model_dump()
            )
            return {"ok": True, "agent_id": child.id}
        elif name == "connect_agents":
            if target not in self.agents:
                raise ValueError("Unknown target agent")
            if args.get("remove"):
                self.network.links = [
                    link
                    for link in self.network.links
                    if not (link.source == agent.id and link.target == target)
                ]
            elif target not in self.neighbors(agent.id):
                self.network.links.append(Link(source=agent.id, target=target))
            self.event(
                "network_changed", action=name, network=self.network.model_dump()
            )
        elif name == "subscribe":
            if args.get("remove"):
                agent.topics = [
                    topic for topic in agent.topics if topic != args["topic"]
                ]
            elif args["topic"] not in agent.topics:
                agent.topics.append(args["topic"])
            self.event(
                "network_changed", action=name, network=self.network.model_dump()
            )
        self.event("orchestration", agent_id=agent.id, action=name, arguments=args)
        return {"ok": True}

    def control(self, action: str):
        if action == "pause":
            self.gate.clear()
            self.state("paused")
        elif action == "resume":
            self.gate.set()
            self.state("running")
        elif action == "cancel" and self.task:
            self.task.cancel()
        else:
            raise ValueError("Unknown control action")

    def respond(self, agent_id: str, text: str):
        future = self.human.get(agent_id)
        if future is None or future.done():
            raise ValueError("Agent is not awaiting human input")
        future.set_result(text)


class Manager:
    def __init__(self, store: Store, transport: Transport | None = None):
        self.store = store
        self.transport = transport or Transport()
        concurrency = int(os.getenv("AGENTICAI_CONCURRENCY", "4"))
        if not 1 <= concurrency <= 64:
            raise ValueError("AGENTICAI_CONCURRENCY must be between 1 and 64")
        self.global_slots = asyncio.Semaphore(concurrency)
        self.runs: dict[str, Run] = {}

    def validate(self, network: Network):
        errors, warnings = [], []
        if not network.agents:
            errors.append("Add at least one agent")
        for agent in network.agents:
            provider = self.store.get("provider", agent.provider_id)
            if agent.kind == "agent" and not provider:
                errors.append(f"{agent.name}: provider not found")
            if (
                provider
                and network.mode == "autonomous"
                and agent.kind == "agent"
                and not (provider["supports_tools"] or provider["kind"] == "demo")
            ):
                errors.append(
                    f"{agent.name}: autonomous mode requires a tool-capable provider"
                )
            for tool in agent.tools + ([agent.tool_id] if agent.kind == "tool" else []):
                if not self.store.get("tool", tool):
                    errors.append(f"{agent.name}: tool not found: {tool}")
            if agent.context_tokens <= agent.max_tokens:
                errors.append(
                    f"{agent.name}: context must exceed output token reservation"
                )
            if (
                provider
                and agent.tools
                and not provider["supports_tools"]
                and provider["kind"] != "demo"
            ):
                warnings.append(
                    f"{agent.name}: tools will not be advertised until provider tool support is enabled"
                )
            if agent.kind == "join" and not any(
                link.target == agent.id for link in network.links
            ):
                errors.append(f"{agent.name}: join requires incoming links")
        if not network.entry_agents and all(
            any(link.target == a.id for link in network.links) for a in network.agents
        ):
            errors.append("Cyclic networks require explicit entry agents")
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def start(self, network: Network, prompt: str | None = None) -> Run:
        prompt = network.initial_task if prompt is None else prompt
        if not prompt.strip():
            raise ValueError("Enter an initial task at the workflow's Start node")
        validation = self.validate(network)
        if not validation["valid"]:
            raise ValueError("; ".join(validation["errors"]))
        provider_ids = {
            agent.provider_id for agent in network.agents if agent.kind == "agent"
        }
        tool_ids = {tool for a in network.agents for tool in a.tools} | {
            a.tool_id for a in network.agents if a.kind == "tool"
        }
        snapshot = {
            "network": network.model_dump(),
            "providers": [self.store.get("provider", id) for id in provider_ids],
            "tools": [self.store.get("tool", id) for id in tool_ids],
        }
        for p in snapshot["providers"]:
            register_references(p.get("api_key_env", ""))
        for t in snapshot["tools"]:
            register_references(*t.get("env", {}).values())
        id = identifier()
        self.store.create_run(id, redact(snapshot), redact(prompt))
        run = Run(self, id, network, prompt, snapshot)
        self.runs[id] = run
        run.task = asyncio.create_task(run.execute())
        run.task.add_done_callback(lambda task: self.runs.pop(id, None))
        return run

    async def close(self):
        tasks = [r.task for r in self.runs.values() if r.task]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.transport.close()
