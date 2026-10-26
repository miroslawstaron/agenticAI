"""Registered argv tools, explicitly enabled shells, and Python plugins."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
import re
import shutil
import signal
import sys
import time
from pathlib import Path

import psutil
from jsonschema import validate

from .models import ExecutionResult, Tool
from .security import redact, register_references


def substitute(text: str, values: dict) -> str:
    """Only ${name} is substituted; JSON braces and shell $ syntax are literal."""

    def replace(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f"Missing argument: {key}")
        value = values[key]
        return value if isinstance(value, str) else json.dumps(value)

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, text)


async def terminate_tree(process: asyncio.subprocess.Process):
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        try:
            root = psutil.Process(process.pid)
            children = root.children(recursive=True)
            for child in reversed(children):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            root.kill()
        except psutil.NoSuchProcess:
            pass
    await process.wait()


def resolve_executable(executable: str) -> str:
    if executable in ("python", "python3", "@python"):
        return sys.executable
    # cmd.exe is the explicit interpreter for Windows batch launchers.
    resolved = shutil.which(executable) or (
        executable if Path(executable).is_file() else ""
    )
    if not resolved:
        raise FileNotFoundError(f"Executable not found: {executable}")
    return resolved


class ToolRunner:
    def __init__(self, root: Path, concurrency: int = 4):
        self.root = Path(root).resolve()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.plugins = {
            ep.name: ep
            for ep in importlib.metadata.entry_points(group="agenticai.tools")
        }

    def plugin_metadata(self):
        result = []
        for name, ep in self.plugins.items():
            try:
                plugin = ep.load()
                metadata = getattr(plugin, "metadata", {})
                result.append({"name": name, **metadata})
            except Exception as exc:
                result.append({"name": name, "error": str(exc)})
        return result

    async def execute(
        self, tool: Tool, arguments: dict, workspace: Path
    ) -> ExecutionResult:
        start = time.perf_counter()
        try:
            validate(arguments, tool.input_schema)
            workspace = Path(workspace).resolve()
            workspace.mkdir(parents=True, exist_ok=True)
            if tool.kind == "python":
                return await self._python(tool, arguments, workspace)
            if tool.kind in ("compiler", "analyzer"):
                return await self._c_tool(tool, arguments, workspace)
            cwd = (
                Path(substitute(tool.cwd, arguments)).expanduser().resolve()
                if tool.cwd
                else workspace
            )
            if not cwd.is_dir():
                raise ValueError(f"Working directory does not exist: {cwd}")
            register_references(*tool.env.values())
            env = self.environment(tool)
            if tool.kind == "shell":
                command = arguments.get("command")
                if not isinstance(command, str):
                    raise ValueError("Shell tools require a string 'command'")
                if os.name == "nt":
                    argv = [
                        resolve_executable(tool.executable or "powershell"),
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        command,
                    ]
                else:
                    argv = [
                        resolve_executable(tool.executable or "bash"),
                        "-c",
                        command,
                    ]
            else:
                executable = shutil.which(
                    tool.executable, path=env["PATH"]
                ) or resolve_executable(tool.executable)
                argv = [executable, *[substitute(arg, arguments) for arg in tool.args]]
                if os.name == "nt" and Path(argv[0]).suffix.lower() in (
                    ".cmd",
                    ".bat",
                    ".ps1",
                ):
                    raise ValueError(
                        "Register batch/PowerShell scripts with an explicit interpreter (cmd.exe /c or powershell -File). Use a shell tool for shell syntax."
                    )
            result = await self.process(
                argv,
                cwd,
                env,
                substitute(tool.stdin, arguments),
                tool.timeout,
                tool.max_output,
                tool.accepted_exit_codes,
            )
            if result.ok and tool.output_format == "json":
                try:
                    result.data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    result.ok, result.error = (
                        False,
                        "Tool output is not valid JSON (or exceeded the output limit)",
                    )
            for pattern in tool.artifacts:
                if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                    raise ValueError(
                        "Artifact patterns must remain inside the working directory"
                    )
                for path in cwd.glob(pattern):
                    if (
                        path.is_file()
                        and path.resolve().is_relative_to(cwd)
                        and not path.is_symlink()
                    ):
                        # Copy explicit shared-directory artifacts into the run workspace.
                        target = workspace / "artifacts" / path.relative_to(cwd)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if path.resolve() != target.resolve():
                            await asyncio.to_thread(shutil.copyfile, path, target)
                        result.artifacts.append(str(target.relative_to(self.root)))
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return ExecutionResult(
                error=redact(str(exc)), duration=time.perf_counter() - start
            )

    def environment(self, tool: Tool) -> dict[str, str]:
        # Deliberately exclude server credentials from subprocess inheritance.
        names = (
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "LANG",
            "LC_ALL",
            "SSL_CERT_FILE",
            "HTTPS_PROXY",
            "HTTP_PROXY",
            "NO_PROXY",
        )
        env = {name: os.environ[name] for name in names if name in os.environ}
        env["PYTHONIOENCODING"] = "utf-8"
        env["PATH"] = os.pathsep.join(
            [
                str(self.root / "tools/python/Scripts"),
                str(self.root / "tools/python/bin"),
                str(self.root / "tools/npm"),
                str(self.root / "tools/npm/bin"),
                env.get("PATH", ""),
            ]
        )
        for name, reference in tool.env.items():
            if reference not in os.environ:
                raise ValueError(f"Environment reference is unset: {reference}")
            env[name] = os.environ[reference]
        return env

    async def process(
        self,
        argv: list[str],
        cwd: Path,
        env: dict,
        stdin: str = "",
        timeout: float = 60,
        max_output: int = 12000,
        accepted: list[int] | None = None,
    ) -> ExecutionResult:
        async with self.semaphore:
            start = time.perf_counter()
            logdir = cwd / "logs"
            logdir.mkdir(exist_ok=True)
            from .models import identifier

            stamp = identifier()
            paths = [logdir / f"{stamp}.stdout.txt", logdir / f"{stamp}.stderr.txt"]
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=cwd,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=os.name != "nt",
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            job = None
            if os.name == "nt":
                from .windows_job import WindowsJob

                try:
                    job = WindowsJob(process.pid)
                except OSError:
                    # A very short-lived process may already have exited.
                    # Living children are still handled by the fallback tree walk.
                    pass
            captured = [bytearray(), bytearray()]

            async def drain(stream, path, index):
                # Bounded accumulation permits redaction across chunk boundaries.
                total = 0
                log = bytearray()
                try:
                    while chunk := await stream.read(8192):
                        if len(captured[index]) < max_output:
                            captured[index].extend(
                                chunk[: max_output - len(captured[index])]
                            )
                        total += len(chunk)
                        available = 16 * 1024 * 1024 - len(log)
                        if available > 0:
                            log.extend(chunk[:available])
                finally:
                    path.write_text(
                        redact(log.decode("utf-8", "replace"))
                        + ("\n[Log truncated at 16 MiB]\n" if total > len(log) else ""),
                        encoding="utf-8",
                    )

            tasks = [
                asyncio.create_task(drain(process.stdout, paths[0], 0)),
                asyncio.create_task(drain(process.stderr, paths[1], 1)),
            ]
            timed_out = False

            async def communicate():
                try:
                    process.stdin.write(stdin.encode("utf-8"))
                    await process.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    process.stdin.close()
                await process.wait()
                await asyncio.gather(*tasks)

            try:
                await asyncio.wait_for(communicate(), timeout)
            except asyncio.TimeoutError:
                timed_out = True
                if job:
                    job.close()
                await terminate_tree(process)
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                if job:
                    job.close()
                await terminate_tree(process)
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            finally:
                if job:
                    job.close()
            return ExecutionResult(
                ok=not timed_out and process.returncode in (accepted or [0]),
                stdout=redact(captured[0].decode("utf-8", "replace")),
                stderr=redact(captured[1].decode("utf-8", "replace")),
                exit_code=process.returncode,
                duration=time.perf_counter() - start,
                timed_out=timed_out,
                artifacts=[str(p.relative_to(self.root)) for p in paths],
                error="Tool timed out"
                if timed_out
                else (
                    ""
                    if process.returncode in (accepted or [0])
                    else f"Process exited with {process.returncode}"
                ),
            )

    async def _c_tool(self, tool: Tool, args: dict, workspace: Path) -> ExecutionResult:
        code = args.get("code", "")
        match = re.search(r"```(?:c|C)\s*\n(.*?)```", code, re.S)
        if match:
            code = match.group(1)
        if not code.strip():
            return ExecutionResult(error="No C code supplied")
        source = workspace / "program.c"
        source.write_text(code, encoding="utf-8")
        if tool.kind == "compiler":
            argv = [
                resolve_executable(tool.executable or "gcc"),
                "-std=c11",
                "-Wall",
                str(source),
                "-o",
                str(workspace / ("program.exe" if os.name == "nt" else "program")),
                "-lm",
            ]
        else:
            argv = [
                resolve_executable(tool.executable or "cppcheck"),
                "--enable=all",
                "--std=c11",
                "--quiet",
                "--suppress=missingIncludeSystem",
                "--error-exitcode=1",
                str(source),
            ]
        result = await self.process(
            argv,
            workspace,
            self.environment(tool),
            timeout=tool.timeout,
            max_output=tool.max_output,
        )
        result.data = {"code": code, "diagnostics": result.stderr}
        result.artifacts.append(str(source.relative_to(self.root)))
        if tool.kind == "compiler":
            binary = workspace / ("program.exe" if os.name == "nt" else "program")
            if result.ok and binary.is_file():
                result.artifacts.append(str(binary.relative_to(self.root)))
        return result

    async def _python(self, tool: Tool, args: dict, workspace: Path) -> ExecutionResult:
        if tool.plugin not in self.plugins:
            return ExecutionResult(error=f"Python plugin not installed: {tool.plugin}")
        # Run plugins in a subprocess so timeout/cancellation also terminate sync plugins.
        input_data = json.dumps(
            {"plugin": tool.plugin, "arguments": args, "workspace": str(workspace)}
        )
        result = await self.process(
            [sys.executable, "-m", "agenticai.plugin_worker"],
            workspace,
            self.environment(tool),
            input_data,
            tool.timeout,
            tool.max_output,
        )
        if result.ok:
            try:
                payload = json.loads(result.stdout)
                result.data = payload
            except ValueError:
                result.ok, result.error = (
                    False,
                    "Plugin must return JSON-serializable output",
                )
        return result
