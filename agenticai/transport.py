"""Reusable HTTP transports and whole-turn context management."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx

from .models import Agent, Provider
from .security import register_references


class ModelError(RuntimeError):
    pass


def bounded_messages(messages: list[dict], budget: int) -> list[dict]:
    """UTF-8 bytes are a conservative token estimate, not provider token accounting.

    Trim complete user turns, never orphaning tool results. Reject an oversized
    latest turn instead of silently dropping instructions or current input.
    """
    system = [m for m in messages if m.get("role") == "system"]
    turns: list[list[dict]] = []
    for message in messages:
        if message.get("role") == "system":
            continue
        if message.get("role") == "user" or not turns:
            turns.append([])
        turns[-1].append(message)

    def cost(items):
        return sum(
            len(json.dumps(item, ensure_ascii=False).encode("utf-8")) + 2
            for item in items
        )

    used = 2 + cost(system)
    selected = []
    for turn in reversed(turns):
        turn_cost = cost(turn)
        if used + turn_cost > budget:
            if selected:
                break
            raise ModelError(
                "Current turn exceeds the context budget. Increase context_tokens, reduce output reservation, or shorten the input/tool output."
            )
        selected.append(turn)
        used += turn_cost
    if used > budget:
        raise ModelError(
            "Current turn exceeds the context budget. Increase context_tokens, reduce output reservation, or shorten the input/tool output."
        )
    return system + [message for turn in reversed(selected) for message in turn]


class EndpointLimiter:
    """Honor the strictest active profile and allow edits once traffic is idle."""

    def __init__(self):
        self.condition = asyncio.Condition()
        self.active = 0
        self.limit = 1

    @asynccontextmanager
    async def slot(self, limit: int):
        async with self.condition:
            self.limit = min(self.limit, limit) if self.active else limit
            while self.active >= self.limit:
                await self.condition.wait()
            self.active += 1
        try:
            yield
        finally:
            async with self.condition:
                self.active -= 1
                self.condition.notify_all()


class Transport:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            limits=httpx.Limits(max_connections=64, max_keepalive_connections=16)
        )
        self.endpoint_locks: dict[str, EndpointLimiter] = {}

    async def close(self):
        await self.client.aclose()

    async def complete(
        self,
        provider: Provider,
        agent: Agent,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        schema_bytes = len(json.dumps(tools or []).encode())
        context = bounded_messages(
            messages, agent.context_tokens - agent.max_tokens - schema_bytes
        )
        if provider.kind == "demo":
            await asyncio.sleep(0.05)
            return self.demo(agent, context, tools or [])
        register_references(provider.api_key_env)
        headers = {}
        if provider.api_key_env:
            key = os.getenv(provider.api_key_env)
            if not key:
                raise ModelError(
                    f"Missing credential environment variable: {provider.api_key_env}"
                )
            headers["Authorization"] = f"Bearer {key}"
        payload: dict[str, Any] = {
            "model": agent.model,
            "messages": context,
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        lock = self.endpoint_locks.setdefault(provider.endpoint, EndpointLimiter())
        async with lock.slot(provider.concurrency):
            for attempt in range(provider.retries + 1):
                try:
                    response = await self.client.post(
                        provider.endpoint,
                        headers=headers,
                        json=payload,
                        timeout=provider.timeout,
                    )
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < provider.retries:
                            retry_after = response.headers.get("Retry-After", "")
                            delay = (
                                min(float(retry_after), 30)
                                if retry_after.isdecimal()
                                else min(0.25 * 2**attempt, 8)
                            )
                            await asyncio.sleep(delay)
                            continue
                    response.raise_for_status()
                    data = response.json()
                    message = data["choices"][0]["message"]
                    if not isinstance(message, dict) or not (
                        isinstance(message.get("content"), str)
                        or message.get("tool_calls")
                    ):
                        raise ValueError("Missing assistant content or tool calls")
                    message = {
                        k: v
                        for k, v in message.items()
                        if k in ("role", "content", "tool_calls")
                    }
                    message["role"] = "assistant"
                    return {"message": message, "usage": data.get("usage", {})}
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    if attempt == provider.retries:
                        raise ModelError(
                            f"Model server unavailable ({type(exc).__name__})"
                        ) from exc
                    await asyncio.sleep(min(0.25 * 2**attempt, 8))
                except httpx.HTTPStatusError as exc:
                    raise ModelError(
                        f"Model server returned HTTP {exc.response.status_code}"
                    ) from exc
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise ModelError(
                        "Model server returned a malformed chat-completion response"
                    ) from exc
        raise ModelError("Request attempts exhausted")

    @staticmethod
    def demo(agent: Agent, messages: list[dict], tools: list[dict]) -> dict:
        last = messages[-1]
        names = {t["function"]["name"] for t in tools}
        if "spawn_agent" in names and not any(m.get("tool_calls") for m in messages):
            call = {
                "id": "demo_spawn",
                "type": "function",
                "function": {
                    "name": "spawn_agent",
                    "arguments": json.dumps(
                        {
                            "name": "Research assistant",
                            "role": "Summarize the delegated task in one paragraph.",
                            "task": str(last.get("content", "")),
                            "tools": [],
                        }
                    ),
                },
            }
            return {
                "message": {"role": "assistant", "content": None, "tool_calls": [call]},
                "usage": {},
            }
        prompt = str(last.get("content", ""))
        if "C programmer" in agent.role:
            text = '```c\n#include <stdio.h>\nint main(void) { puts("Hello from AgenticAI"); return 0; }\n```'
        elif last.get("role") == "tool":
            text = f"{agent.name}: Tool completed. {prompt[:500]}"
        else:
            text = f"{agent.name}: Reviewed the task. {prompt[:600]}\nNext step: verify the result and record the evidence."
        return {"message": {"role": "assistant", "content": text}, "usage": {}}
