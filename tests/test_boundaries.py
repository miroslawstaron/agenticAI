import asyncio
import json

import httpx
import pytest

from agenticai.models import Agent, Link, Network, Provider, Tool
from agenticai.transport import Transport


async def test_native_tool_call_roundtrip(manager):
    received = []

    def handler(request):
        body = json.loads(request.content)
        received.append(body)
        if len(received) == 1:
            name = body["tools"][0]["function"]["name"]
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call1",
                                        "type": "function",
                                        "function": {"name": name, "arguments": "{}"},
                                    }
                                ],
                            }
                        }
                    ]
                },
            )
        assert body["messages"][-1]["role"] == "tool"
        assert body["messages"][-1]["tool_call_id"] == "call1"
        assert json.loads(body["messages"][-1]["content"])["ok"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "verified"}}]
            },
        )

    await manager.transport.close()
    manager.transport = Transport(
        httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    manager.store.put(
        "provider", "native", Provider(id="native", kind="http", supports_tools=True)
    )
    run = manager.start(
        Network(
            agents=[Agent(id="a", provider_id="native", tools=["python-version"])],
            entry_agents=["a"],
        ),
        "task",
    )
    await run.task
    assert run.status == "completed", manager.store.run(run.id)
    assert len(received) == 2
    assert manager.store.messages(run.id, "a")[-1]["content"] == "verified"


async def test_pause_excludes_budget_at_model_checkpoint(manager):
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def completion(provider, agent, messages, tools):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await release.wait()
            name = tools[0]["function"]["name"]
            return {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c",
                            "type": "function",
                            "function": {"name": name, "arguments": "{}"},
                        }
                    ],
                },
                "usage": {},
            }
        return {"message": {"role": "assistant", "content": "done"}, "usage": {}}

    manager.transport.complete = completion
    network = Network(
        agents=[Agent(id="a", tools=["python-version"])], entry_agents=["a"]
    )
    network.limits.active_seconds = 0.4
    run = manager.start(network, "task")
    await entered.wait()
    run.control("pause")
    release.set()
    await asyncio.sleep(0.6)
    assert calls == 1 and run.status == "paused"
    run.control("resume")
    await run.task
    assert run.status == "completed", manager.store.run(run.id)


async def test_incomplete_join_and_failed_tool_step(manager):
    network = Network(
        agents=[Agent(id="a"), Agent(id="b"), Agent(id="join", kind="join")],
        links=[Link(source="a", target="join"), Link(source="b", target="join")],
        entry_agents=["a"],
    )
    run = manager.start(network, "task")
    await run.task
    assert (
        run.status == "failed"
        and "Join is missing" in manager.store.run(run.id)["error"]
    )
    manager.store.put(
        "tool", "missing", Tool(id="missing", executable="definitely-missing-987")
    )
    run = manager.start(
        Network(
            agents=[Agent(id="t", kind="tool", tool_id="missing")], entry_agents=["t"]
        ),
        "task",
    )
    await run.task
    assert (
        run.status == "failed"
        and "Executable not found" in manager.store.run(run.id)["error"]
    )


def test_path_safe_ids_and_json_schema():
    with pytest.raises(ValueError, match="IDs must"):
        Agent(id="../../outside")
    with pytest.raises(ValueError, match="Invalid JSON Schema"):
        Tool(input_schema={"type": "not-a-type"})


def test_restore_manifest_api(tmp_path):
    from fastapi.testclient import TestClient

    from agenticai.api import create_app

    with TestClient(create_app(tmp_path)) as client:
        client.headers["X-Studio-Token"] = client.get("/api/v1/session").json()["token"]
        response = client.post(
            "/api/v1/installations/restore-preview",
            json={
                "schema_version": 1,
                "tools": [
                    {"manager": "pip", "package": "ruff", "resolved_version": "0.14.0"}
                ],
            },
        )
        assert response.status_code == 200
        assert response.json()[0]["argv"][-1] == "ruff==0.14.0"
