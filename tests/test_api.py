import time

import pytest
from fastapi.testclient import TestClient

from agenticai.api import create_app
from agenticai.models import Agent, Network, Tool
from agenticai.store import Store


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "studio")) as client:
        client.headers["X-Studio-Token"] = client.get("/api/v1/session").json()["token"]
        yield client


def test_session_origin_and_host_protection(client):
    assert client.get("/api/v1/session").headers["cache-control"] == "no-store"
    token = client.headers.pop("X-Studio-Token")
    rejected = client.post("/api/v1/networks/validate", json={})
    assert rejected.status_code == 403
    assert rejected.headers["x-studio-session"] == "renew"
    client.headers["X-Studio-Token"] = token
    assert (
        client.post(
            "/api/v1/networks/validate",
            json={},
            headers={"Origin": "https://untrusted.example"},
        ).status_code
        == 403
    )
    assert client.get("/health", headers={"Host": "rebind.example"}).status_code == 400
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").headers["x-frame-options"] == "DENY"
    assert client.get("/tutorial/").headers["x-frame-options"] == "SAMEORIGIN"


def test_expired_session_rejects_before_mutation_and_can_be_renewed(client):
    network = Network(id="renewed", initial_task="Build a small program")
    response = client.put(
        "/api/v1/networks/renewed",
        json=network.model_dump(),
        headers={"X-Studio-Token": "token-from-before-server-restart"},
    )
    assert response.status_code == 403
    assert response.headers["x-studio-session"] == "renew"
    assert client.get("/api/v1/networks/renewed").status_code == 404
    token = client.get("/api/v1/session").json()["token"]
    assert (
        client.put(
            "/api/v1/networks/renewed",
            json=network.model_dump(),
            headers={"X-Studio-Token": token},
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/networks/renewed").json()["initial_task"]
        == network.initial_task
    )


def test_start_run_uses_saved_initial_task_and_allows_override(client):
    network = Network(
        id="task",
        agents=[Agent(id="programmer")],
        entry_agents=["programmer"],
        initial_task="Implement a Unicode greeting: Hej världen!",
    )
    for body, expected in (
        ({"network": network.model_dump()}, network.initial_task),
        (
            {"network": network.model_dump(), "prompt": "Run-specific task"},
            "Run-specific task",
        ),
    ):
        response = client.post("/api/v1/runs", json=body)
        assert response.status_code == 200, response.text
        details = client.get("/api/v1/runs/" + response.json()["id"]).json()
        assert details["prompt"] == expected
        assert details["snapshot"]["network"]["initial_task"] == network.initial_task
    network.initial_task = " \n "
    assert (
        client.post("/api/v1/runs", json={"network": network.model_dump()}).status_code
        == 422
    )


def test_crud_network_validation_and_tool_test(client):
    network = Network(id="test", agents=[Agent(id="a")], entry_agents=["a"])
    assert (
        client.put("/api/v1/networks/test", json=network.model_dump()).status_code
        == 200
    )
    assert client.get("/api/v1/networks/test").json()["name"] == network.name
    assert client.post("/api/v1/networks/validate", json=network.model_dump()).json()[
        "valid"
    ]
    tool = Tool(
        id="json",
        executable="@python",
        args=["-c", "print('{\"value\":42}')"],
        output_format="json",
    )
    assert client.put("/api/v1/tools/json", json=tool.model_dump()).status_code == 200
    result = client.post("/api/v1/tools/json/test", json={}).json()
    assert result["ok"] and result["data"] == {"value": 42}
    assert client.get("/api/v1/tools/json/availability").json()["available"]
    assert client.get("/api/v1/artifacts/" + result["artifacts"][0]).status_code == 200
    assert client.get("/api/v1/artifacts/studio.sqlite3").status_code == 404
    assert client.delete("/api/v1/networks/test").json()["ok"]


def test_run_exports_and_sse_reconnect(client):
    network = client.get("/api/v1/networks/teacher-student").json()
    id = client.post(
        "/api/v1/runs",
        json={"network": network, "prompt": "hello <script>alert(1)</script>"},
    ).json()["id"]
    for _ in range(100):
        details = client.get("/api/v1/runs/" + id).json()
        if details["status"] == "completed":
            break
        time.sleep(0.02)
    assert details["status"] == "completed", details
    assert len(details["messages"]) == 10
    events = client.get(f"/api/v1/runs/{id}/events?stream=false").json()
    cursor = events[1]["seq"]
    with client.stream(
        "GET", f"/api/v1/runs/{id}/events", headers={"Last-Event-ID": str(cursor)}
    ) as response:
        text = "".join(response.iter_text())
        assert f"id: {cursor}\n" not in text and "event: end" in text
    assert client.get(f"/api/v1/runs/{id}/export/json").json()["messages"]
    assert "agent_id" in client.get(f"/api/v1/runs/{id}/export/csv").text
    html = client.get(f"/api/v1/runs/{id}/export/html").text
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert client.get(f"/api/v1/runs/{id}/control/pause").status_code in (404, 405)
    assert client.post(f"/api/v1/runs/{id}/control/pause").status_code == 409


def test_installation_preview_and_confirmation(client):
    body = {
        "manager": "pip",
        "package": "ruff",
        "version": "",
        "source": "",
        "action": "install",
        "recipe_id": "",
    }
    plan = client.post("/api/v1/installations/preview", json=body).json()
    assert "pip" in plan["argv"] and "confirmation" in plan
    assert (
        client.post(
            "/api/v1/installations", json={"request": body, "confirmation": "invalid"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/installations/preview",
            json={**body, "package": "-r requirements.txt"},
        ).status_code
        == 422
    )
    assert client.get("/api/v1/installations/manifest").json()["schema_version"] == 1


def test_restart_marks_interrupted(tmp_path):
    store = Store(tmp_path)
    store.create_run("r", {"network": {}}, "task")
    store.update_run("r", "waiting")
    store.put("installation", "i", {"id": "i", "status": "running"})
    store.close()
    store = Store(tmp_path)
    assert store.run("r")["status"] == "interrupted"
    assert store.get("installation", "i")["status"] == "interrupted"
    store.close()
