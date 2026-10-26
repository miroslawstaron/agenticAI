import json
import os
import sys

import httpx
import pytest

from agent import AgentAI
from agentCompiler import AgentCompiler
from agenticai.installations import Installations
from agenticai.models import InstallRequest, Recipe, Tool
from agenticai.tools import ToolRunner
from agentStaticAnalyzer import AgentStaticAnalyzer


async def test_install_recipe_jobs_and_manifest(store):
    runner = ToolRunner(store.root)
    manager = Installations(store, runner)
    store.put(
        "recipe",
        "test",
        Recipe(
            id="test",
            name="fixture",
            executable=sys.executable,
            install_args=["-c", "print('installed')"],
            remove_args=["-c", "print('removed')"],
        ),
    )
    req = InstallRequest(manager="recipe", package="fixture", recipe_id="test")
    plan = manager.preview(req)
    job = manager.start(req, plan["confirmation"])
    await manager.tasks[job["id"]]
    assert store.get("installation", job["id"])["status"] == "completed"
    assert manager.manifest()["tools"][0]["package"] == "fixture"
    req = req.model_copy(update={"action": "remove"})
    plan = manager.preview(req)
    job = manager.start(req, plan["confirmation"])
    await manager.tasks[job["id"]]
    assert manager.manifest()["tools"] == []


async def test_failed_installation_preserves_logs(store):
    manager = Installations(store, ToolRunner(store.root))
    store.put(
        "recipe",
        "fail",
        Recipe(
            id="fail",
            name="failure",
            executable=sys.executable,
            install_args=[
                "-c",
                "import sys;print('permission denied',file=sys.stderr);sys.exit(5)",
            ],
        ),
    )
    req = InstallRequest(manager="recipe", package="fixture", recipe_id="fail")
    job = manager.start(req, manager.preview(req)["confirmation"])
    await manager.tasks[job["id"]]
    result = store.get("installation", job["id"])
    assert (
        result["status"] == "failed"
        and "permission denied" in result["result"]["stderr"]
    )
    assert manager.manifest()["tools"] == []


def test_package_manager_previews_and_validation(store):
    manager = Installations(store, ToolRunner(store.root))
    for backend, package in [("pip", "ruff"), ("npm", "@scope/package")]:
        plan = manager.preview(
            InstallRequest(manager=backend, package=package, version="1.0.0")
        )
        assert "1.0.0" in " ".join(plan["argv"])
    if os.name == "nt":
        plan = manager.preview(InstallRequest(manager="winget", package="Git.Git"))
        assert "--accept-package-agreements" not in plan["argv"]
        assert "--disable-interactivity" in plan["argv"]
    with pytest.raises(ValueError):
        manager.preview(InstallRequest(manager="apt", package="jq"))
    with pytest.raises(ValueError):
        manager.preview(
            InstallRequest(manager="pip", package="https://example.com/evil.whl")
        )


def test_legacy_pooled_requests_and_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "private-key")
    agent = AgentAI("http://test/v1/chat/completions", "model", "policy", max_tokens=17)
    original = agent._client

    def handler(request):
        assert request.headers["Authorization"] == "Bearer private-key"
        assert json.loads(request.content)["max_tokens"] == 17
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "hello\n$world"}}]}
        )

    agent._client = httpx.Client(transport=httpx.MockTransport(handler))
    original.close()
    assert agent.get_response("task") == "hello\n$world"
    assert agent.get_response(None) is None
    assert len(agent.messages) == 3
    agent.save_to_csv(tmp_path / "out.csv")
    agent.to_html(tmp_path / "out.html")
    assert "hello" in (tmp_path / "out.html").read_text()
    agent.close()


def test_legacy_compiler_repairs_and_rechecks(monkeypatch):
    checked = []

    def check(self, code, directory):
        checked.append(code)
        return {
            "ok": code == "int main(void){return 0;}",
            "diagnostics": "fix me",
            "exit_code": 0 if len(checked) > 1 else 1,
        }

    monkeypatch.setattr(AgentCompiler, "_check", check)
    monkeypatch.setattr(
        AgentAI,
        "get_response",
        lambda self, prompt: "```c\nint main(void){return 0;}\n```",
    )
    compiler = AgentCompiler("http://test", "model", 3)
    assert compiler.get_response("bad") == "int main(void){return 0;}"
    assert (
        checked == ["bad", "int main(void){return 0;}"] and compiler.last_result["ok"]
    )
    compiler.close()


def test_legacy_analyzer_applies_repair(monkeypatch):
    checked = []

    def check(self, code, directory):
        checked.append(code)
        return {
            "ok": code == "fixed",
            "diagnostics": "analyzer finding",
            "exit_code": 1,
        }

    monkeypatch.setattr(AgentStaticAnalyzer, "_check", check)
    monkeypatch.setattr(AgentAI, "get_response", lambda self, prompt: "fixed")
    analyzer = AgentStaticAnalyzer("http://test", "model", 2)
    assert analyzer.get_response("bad") == "fixed"
    assert checked == ["bad", "fixed"] and analyzer.last_result["ok"]
    analyzer.close()


async def test_python_plugin_subprocess(store, monkeypatch, tmp_path):
    package = tmp_path / "plugin"
    package.mkdir()
    (package / "fixture_plugin.py").write_text(
        "async def execute(arguments,workspace):\n    return {'answer':arguments['value']*2}\n",
        encoding="utf-8",
    )
    dist = package / "fixture_plugin-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Name: fixture-plugin\nVersion: 1.0\n")
    (dist / "entry_points.txt").write_text(
        "[agenticai.tools]\nfixture = fixture_plugin\n"
    )
    monkeypatch.syspath_prepend(str(package))
    monkeypatch.setenv("FIXTURE_PYTHONPATH", str(package))
    runner = ToolRunner(store.root)
    tool = Tool(
        kind="python", plugin="fixture", env={"PYTHONPATH": "FIXTURE_PYTHONPATH"}
    )
    result = await runner.execute(tool, {"value": 21}, store.root / "plugin-test")
    assert result.ok and result.data == {"answer": 42}, result
