import asyncio
import json
import os

import psutil
import pytest

from agenticai.models import Tool
from agenticai.tools import ToolRunner


@pytest.fixture
def runner(tmp_path):
    return ToolRunner(tmp_path)


def python_tool(code, **kwargs):
    return Tool(executable="@python", args=["-c", code], **kwargs)


async def test_literal_arguments_stdin_unicode_env_and_json(
    runner, tmp_path, monkeypatch
):
    monkeypatch.setenv("AGENTIC_TEST_SETTING", "visible-setting")
    tool = python_tool(
        "import json,sys,os;print(json.dumps([sys.argv[1],sys.stdin.read(),os.environ['SETTING']],ensure_ascii=False))",
        stdin="${text}",
        env={"SETTING": "AGENTIC_TEST_SETTING"},
        output_format="json",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}, "arg": {"type": "string"}},
            "required": ["text", "arg"],
        },
    )
    tool.args.append("${arg}")
    result = await runner.execute(
        tool,
        {"text": "Hej 世界\n", "arg": "a b; $(touch nope) & `whoami`"},
        tmp_path / "work",
    )
    assert result.ok, result
    assert result.data == ["a b; $(touch nope) & `whoami`", "Hej 世界\n", "[REDACTED]"]
    assert not (tmp_path / "work/nope").exists()


async def test_failure_and_accepted_code(runner, tmp_path):
    result = await runner.execute(
        python_tool("import sys;print('bad',file=sys.stderr);sys.exit(7)"),
        {},
        tmp_path / "a",
    )
    assert not result.ok and result.exit_code == 7 and "bad" in result.stderr
    result = await runner.execute(
        python_tool("import sys;sys.exit(7)", accepted_exit_codes=[7]),
        {},
        tmp_path / "b",
    )
    assert result.ok


async def test_artifact_large_logs_and_output_limit(runner, tmp_path):
    result = await runner.execute(
        python_tool(
            "from pathlib import Path;Path('answer.json').write_text('{\"ok\":true}');print('x'*40000)",
            artifacts=["*.json"],
            max_output=256,
        ),
        {},
        tmp_path / "work",
    )
    assert result.ok and len(result.stdout) <= 256
    assert len(result.artifacts) == 3
    assert (tmp_path / result.artifacts[0]).stat().st_size > 40000
    assert json.loads((tmp_path / result.artifacts[-1]).read_text()) == {"ok": True}


async def test_timeout_kills_process_tree(runner, tmp_path):
    code = "import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path('child.pid').write_text(str(p.pid));time.sleep(30)"
    result = await runner.execute(python_tool(code, timeout=0.5), {}, tmp_path / "work")
    assert result.timed_out and not result.ok
    pid = int((tmp_path / "work/child.pid").read_text())
    await asyncio.sleep(0.1)
    assert (
        not psutil.pid_exists(pid)
        or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    )


async def test_cancellation_kills_process_tree(runner, tmp_path):
    task = asyncio.create_task(
        runner.execute(
            python_tool(
                "import time,os;from pathlib import Path;Path('pid').write_text(str(os.getpid()));time.sleep(30)"
            ),
            {},
            tmp_path / "work",
        )
    )
    for _ in range(100):
        if (tmp_path / "work/pid").exists():
            break
        await asyncio.sleep(0.01)
    pid = int((tmp_path / "work/pid").read_text())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (
        not psutil.pid_exists(pid)
        or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    )


async def test_exited_parent_does_not_leave_child_holding_pipes(runner, tmp_path):
    code = "import subprocess,sys;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path('child.pid').write_text(str(p.pid))"
    result = await runner.execute(
        python_tool(code, timeout=0.5), {}, tmp_path / "orphan"
    )
    pid = int((tmp_path / "orphan/child.pid").read_text())
    await asyncio.sleep(0.1)
    assert result.timed_out
    assert (
        not psutil.pid_exists(pid)
        or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    )


async def test_explicit_shell(runner, tmp_path):
    command = (
        "'hello' | ForEach-Object { $_.ToUpper() }"
        if os.name == "nt"
        else "printf hello | tr a-z A-Z"
    )
    result = await runner.execute(
        Tool(kind="shell", input_schema={"type": "object", "required": ["command"]}),
        {"command": command},
        tmp_path / "work",
    )
    assert result.ok and "HELLO" in result.stdout


async def test_missing_executable_and_invalid_schema(runner, tmp_path):
    result = await runner.execute(
        Tool(executable="agenticai-certainly-missing-123"), {}, tmp_path / "a"
    )
    assert not result.ok and "not found" in result.error
    result = await runner.execute(
        Tool(
            executable="@python",
            input_schema={"type": "object", "required": ["missing"]},
        ),
        {},
        tmp_path / "b",
    )
    assert not result.ok and "required" in result.error


async def test_secret_redaction_and_no_ambient_key(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("EXAMPLE_API_KEY", "sensitive-key-content")
    result = await runner.execute(
        python_tool("import os;print(os.getenv('EXAMPLE_API_KEY','absent'))"),
        {},
        tmp_path / "a",
    )
    assert result.stdout.strip() == "absent"
    result = await runner.execute(
        python_tool(
            "import os;print(os.environ['KEY'])", env={"KEY": "EXAMPLE_API_KEY"}
        ),
        {},
        tmp_path / "b",
    )
    assert "sensitive-key-content" not in result.model_dump_json()
    assert "sensitive-key-content" not in (tmp_path / result.artifacts[0]).read_text()


async def test_concurrent_compilation_isolated(runner, tmp_path):
    import shutil

    if not shutil.which("gcc"):
        pytest.skip("GCC not installed")
    tool = Tool(kind="compiler", input_schema={"type": "object", "required": ["code"]})
    results = await asyncio.gather(
        *[
            runner.execute(
                tool, {"code": f"int main(void){{return {i};}}"}, tmp_path / f"c{i}"
            )
            for i in range(3)
        ]
    )
    assert all(r.ok for r in results), results
    assert len({r.artifacts[-1] for r in results}) == 3


async def test_redacts_secrets_across_read_chunks(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("BOUNDARY_SECRET", "super-private-boundary-value")
    tool = python_tool(
        "import os,sys;sys.stdout.write('x'*16380+os.environ['VALUE']+'y'*9000)",
        env={"VALUE": "BOUNDARY_SECRET"},
        max_output=30000,
    )
    result = await runner.execute(tool, {}, tmp_path / "boundary")
    assert result.ok
    assert "super-private-boundary-value" not in result.stdout
    assert (
        "super-private-boundary-value"
        not in (tmp_path / result.artifacts[0]).read_text()
    )


async def test_compile_failure_and_missing_analyzer(runner, tmp_path):
    result = await runner.execute(
        Tool(kind="compiler"), {"code": "bad C code"}, tmp_path / "c"
    )
    assert not result.ok
    result = await runner.execute(
        Tool(kind="analyzer", executable="missing-cppcheck-123"),
        {"code": "int main(void){return 0;}"},
        tmp_path / "s",
    )
    assert not result.ok and "not found" in result.error
