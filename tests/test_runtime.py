import asyncio
import json

import pytest

from agenticai.models import Agent, Link, Network, Provider, Tool
from agenticai.runtime import Run


async def wait_status(run, status):
    for _ in range(200):
        if run.status == status:
            return
        if run.task.done():
            break
        await asyncio.sleep(0.01)
    assert run.status == status, run.store.run(run.id)


async def test_teacher_student_termination_and_transcripts(manager, store):
    network = Network.model_validate(store.get("network", "teacher-student"))
    run = manager.start(network, "Solve this problem")
    await run.task
    assert run.status == "completed", store.run(run.id)
    assert run.visits == {"student": 2, "teacher": 2}
    assert len(store.messages(run.id, "student")) == 5
    assert store.run(run.id)["snapshot"]["network"] == network.model_dump()


async def test_programmer_designer_start_and_feedback_preserve_task(manager, store):
    network = Network.model_validate(store.get("network", "designer-programmer"))
    network.initial_task = (
        "Print a Unicode greeting and keep literal {message} and {task} text."
    )
    run = manager.start(network)
    await run.task
    assert run.status == "completed", store.run(run.id)
    assert run.visits == {"programmer": 3, "designer": 3}
    assert store.messages(run.id, "programmer")[1]["content"] == network.initial_task
    review = store.messages(run.id, "designer")[1]["content"]
    assert network.initial_task in review
    assert "#include <stdio.h>" in review
    started = [
        e["body"]["agent_id"]
        for e in store.events(run.id)
        if e["kind"] == "agent_started"
    ]
    assert started == ["programmer", "designer"] * 3


async def test_initial_task_sent_to_each_selected_first_recipient(manager):
    network = Network(
        agents=[Agent(id="a"), Agent(id="b"), Agent(id="unused")],
        entry_agents=["a", "b"],
        initial_task="Work independently on this task",
    )
    run = manager.start(network)
    await run.task
    for id in ("a", "b"):
        assert manager.store.messages(run.id, id)[1]["content"] == network.initial_task
    assert run.visits["unused"] == 0


async def test_parallel_fork_and_join(manager):
    agents = [
        Agent(id="root"),
        Agent(id="a"),
        Agent(id="b"),
        Agent(id="join", kind="join"),
        Agent(id="out"),
    ]
    links = [
        Link(source=a, target=b)
        for a, b in [
            ("root", "a"),
            ("root", "b"),
            ("a", "join"),
            ("b", "join"),
            ("join", "out"),
        ]
    ]
    run = manager.start(
        Network(agents=agents, links=links, entry_agents=["root"]), "task"
    )
    await run.task
    assert run.status == "completed", run.store.run(run.id)
    joined = run.store.messages(run.id, "join")[-1]["content"]
    assert "From a" in joined and "From b" in joined
    assert run.visits["out"] == 1


async def test_conditions(manager):
    network = Network(
        agents=[Agent(id="a"), Agent(id="b"), Agent(id="c")],
        links=[
            Link(source="a", target="b", condition="contains", value="Reviewed"),
            Link(source="a", target="c", condition="contains", value="not present"),
        ],
        entry_agents=["a"],
    )
    run = manager.start(network, "task")
    await run.task
    assert run.visits["b"] == 1 and run.visits["c"] == 0


async def test_human_wait_excludes_time_and_responds(manager):
    network = Network(agents=[Agent(id="human", kind="human")], entry_agents=["human"])
    network.limits.active_seconds = 0.15
    run = manager.start(network, "Review this")
    await wait_status(run, "waiting")
    await asyncio.sleep(0.25)
    run.respond("human", "approved")
    await run.task
    assert run.status == "completed", manager.store.run(run.id)
    assert run.active < 0.15
    assert run.store.messages(run.id)[-1]["content"] == "approved"


async def test_pause_resume_and_cancel(manager):
    run = manager.start(
        Network(agents=[Agent(id="human", kind="human")], entry_agents=["human"]),
        "review",
    )
    await wait_status(run, "waiting")
    run.control("pause")
    assert run.status == "paused"
    run.control("resume")
    run.control("cancel")
    await run.task
    assert run.status == "cancelled" and not run.human


async def test_model_call_limit(manager):
    network = Network.model_validate(manager.store.get("network", "teacher-student"))
    network.limits.max_calls = 1
    run = manager.start(network, "task")
    await run.task
    assert run.status == "limited" and run.calls == 1


async def test_active_time_limit(manager, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(10)

    monkeypatch.setattr(manager.transport, "complete", slow)
    network = Network(agents=[Agent(id="a")], entry_agents=["a"])
    network.limits.active_seconds = 0.1
    run = manager.start(network, "task")
    await run.task
    assert run.status == "limited"


async def test_autonomous_spawn_delegation_and_snapshot(manager):
    network = Network.model_validate(manager.store.get("network", "autonomous-team"))
    run = manager.start(network, "Research this task")
    await run.task
    assert run.status == "completed", manager.store.run(run.id)
    assert len(run.network.agents) == 2
    assert len(manager.store.run(run.id)["snapshot"]["network"]["agents"]) == 1
    assert any(
        "Delegated result" in (m.get("content") or "")
        for m in manager.store.messages(run.id, "coordinator")
    )


async def test_capability_restrictions_and_message_routing(manager):
    network = Network(
        mode="autonomous",
        agents=[
            Agent(id="a", can_orchestrate=True, tools=["compiler"]),
            Agent(id="b", topics=["research"]),
        ],
        entry_agents=["a"],
    )
    snapshot = {
        "providers": [manager.store.get("provider", "demo")],
        "tools": [manager.store.get("tool", "compiler")],
    }
    run = Run(manager, "unit", network, "task", snapshot)
    a = run.agents["a"]
    with pytest.raises(ValueError, match="Connect"):
        run._orchestrate(a, "send_message", {"target": "b", "message": "hello"})
    run._orchestrate(a, "connect_agents", {"target": "b"})
    run._orchestrate(a, "publish", {"topic": "research", "message": "published"})
    run._orchestrate(a, "broadcast", {"message": "broadcast"})
    assert [i["message"] for i in run.inbox] == ["published", "broadcast"]
    with pytest.raises(ValueError, match="subset"):
        run._orchestrate(
            a, "spawn_agent", {"name": "bad", "role": "role", "tools": ["shell"]}
        )
    result = run._orchestrate(
        a, "spawn_agent", {"name": "child", "role": "role", "tools": ["compiler"]}
    )
    child = run.agents[result["agent_id"]]
    assert (
        child.tools == ["compiler"]
        and child.provider_id == a.provider_id
        and not child.can_orchestrate
    )
    run._orchestrate(a, "delegate", {"target": "b", "task": "delegate task"})
    assert run.delegations["b"] == "a"
    run._orchestrate(a, "subscribe", {"topic": "new"})
    assert "new" in a.topics
    run._orchestrate(a, "connect_agents", {"target": "b", "remove": True})
    assert "b" not in run.neighbors("a")


async def test_tool_step_and_secret_persistence(manager, monkeypatch):
    monkeypatch.setenv("MY_TEST_SECRET", "hide-this-credential")
    tool = Tool(
        id="echo",
        executable="@python",
        args=["-c", "import os;print(os.environ['VALUE'])"],
        env={"VALUE": "MY_TEST_SECRET"},
    )
    manager.store.put("tool", tool.id, tool)
    network = Network(
        agents=[Agent(id="t", kind="tool", tool_id="echo")], entry_agents=["t"]
    )
    run = manager.start(network, "task")
    await run.task
    assert run.status == "completed"
    assert "hide-this-credential" not in json.dumps(manager.store.events(run.id))
    assert "hide-this-credential" not in json.dumps(manager.store.messages(run.id))


async def test_incompatible_provider_and_invalid_graph(manager):
    manager.store.put(
        "provider", "plain", Provider(id="plain", kind="http", supports_tools=False)
    )
    network = Network(mode="autonomous", agents=[Agent(provider_id="plain")])
    assert not manager.validate(network)["valid"]
    with pytest.raises(ValueError):
        manager.start(network, "task")
    with pytest.raises(ValueError, match="existing"):
        Network(agents=[Agent(id="a")], links=[Link(source="a", target="missing")])
