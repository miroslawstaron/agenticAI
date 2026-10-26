import pytest

from agenticai.models import Agent, Link, Network


async def test_join_drains_multiple_complete_sets(manager):
    network = Network(
        agents=[Agent(id="a"), Agent(id="b"), Agent(id="join", kind="join")],
        entry_agents=["a", "b"],
        links=[Link(source=source, target="join") for source in ["a", "a", "b", "b"]],
    )
    run = manager.start(network, "task")
    await run.task
    assert run.status == "completed", manager.store.run(run.id)
    assert run.visits["join"] == 2


async def test_global_concurrency_configurable(store, monkeypatch):
    from agenticai.runtime import Manager

    monkeypatch.setenv("AGENTICAI_CONCURRENCY", "8")
    manager = Manager(store)
    assert manager.global_slots._value == 8
    await manager.close()
    monkeypatch.setenv("AGENTICAI_CONCURRENCY", "0")
    with pytest.raises(ValueError):
        Manager(store)
