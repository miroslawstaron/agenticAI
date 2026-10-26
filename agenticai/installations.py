"""User-initiated, previewable installation jobs. Never exposed as agent tools."""

import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import httpx

from .models import InstallRequest, Recipe, Tool, identifier
from .security import redact
from .store import Store
from .tools import ToolRunner


class Installations:
    def __init__(self, store: Store, runner: ToolRunner):
        self.store, self.runner = store, runner
        self.tasks: dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()

    def preview(self, request: InstallRequest) -> dict:
        package, version = request.package, request.version
        if request.manager == "pip":
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", package):
                raise ValueError("pip requires a package name, not a URL or local path")
            python = (
                self.store.root
                / "tools/python"
                / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            )
            argv = [str(python), "-m", "pip"]
            if request.action == "remove":
                argv += ["uninstall", "-y", package]
            else:
                argv += ["install", "--disable-pip-version-check"]
                if request.action == "update":
                    argv.append("--upgrade")
                if request.source:
                    if not request.source.startswith("https://"):
                        raise ValueError("pip sources must be HTTPS index URLs")
                    argv += ["--index-url", request.source]
                argv.append(package + (f"=={version}" if version else ""))
        elif request.manager == "npm":
            if not re.fullmatch(r"(?:@[A-Za-z0-9_.-]+/)?[A-Za-z0-9_.-]+", package):
                raise ValueError("npm requires a registry package name")
            node = shutil.which("node")
            npm = shutil.which("npm")
            cli = (
                Path(node).parent / "node_modules/npm/bin/npm-cli.js"
                if node
                else Path("__missing__")
            )
            argv = (
                [node, str(cli)]
                if cli.is_file()
                else (
                    ["cmd.exe", "/d", "/c", npm or "npm"]
                    if os.name == "nt"
                    else [npm or "npm"]
                )
            )
            action = "uninstall" if request.action == "remove" else "install"
            argv += [
                action,
                "--global",
                "--prefix",
                str(self.store.root / "tools/npm"),
                package
                + (f"@{version}" if version and request.action != "remove" else ""),
            ]
            if request.source:
                if not request.source.startswith("https://"):
                    raise ValueError("npm sources must be HTTPS registry URLs")
                argv += ["--registry", request.source]
        elif request.manager == "winget":
            if os.name != "nt":
                raise ValueError(
                    "WinGet is available only in standalone Windows installations"
                )
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", package):
                raise ValueError("Use an exact WinGet package identifier")
            action = {"install": "install", "update": "upgrade", "remove": "uninstall"}[
                request.action
            ]
            argv = [
                shutil.which("winget") or "winget",
                action,
                "--id",
                package,
                "--exact",
                "--disable-interactivity",
            ]
            if request.action != "remove":
                argv += ["--scope", "user"]
            if version and request.action == "install":
                argv += ["--version", version]
            if request.source:
                argv += ["--source", request.source]
        elif request.manager == "apt":
            if not os.getenv("AGENTICAI_INSTALLER_SOCKET"):
                raise ValueError(
                    "System package installation requires the Docker installer helper"
                )
            if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?", package):
                raise ValueError("Invalid Debian package identifier")
            if version and not re.fullmatch(r"[A-Za-z0-9:.+~_-]+", version):
                raise ValueError("Invalid Debian package version")
            if request.source:
                raise ValueError("APT sources belong in the image configuration")
            argv = [
                "apt-get",
                "remove" if request.action == "remove" else "install",
                "--yes",
                "--no-install-recommends",
                package
                + (f"={version}" if version and request.action != "remove" else ""),
            ]
        else:
            data = self.store.get("recipe", request.recipe_id)
            if not data:
                raise ValueError("Select an installation recipe")
            recipe = Recipe.model_validate(data)
            args = getattr(recipe, request.action + "_args")
            if not args:
                raise ValueError("This recipe does not support the selected action")
            from .tools import substitute

            argv = [
                recipe.executable,
                *[substitute(arg, request.model_dump()) for arg in args],
            ]
        plan = {
            "request": request.model_dump(),
            "argv": argv,
            "environment": "container" if os.getenv("AGENTICAI_CONTAINER") else "host",
            "agreements": "Package agreements are not automatically accepted. Interactive/elevated installers must be completed outside the app if required.",
        }
        plan["confirmation"] = hashlib.sha256(
            json.dumps(plan, sort_keys=True).encode()
        ).hexdigest()
        return plan

    def start(self, request: InstallRequest, confirmation: str) -> dict:
        plan = self.preview(request)
        if confirmation != plan["confirmation"]:
            raise ValueError(
                "Preview the current installation command before confirming"
            )
        id = identifier()
        job = {"id": id, "status": "queued", "created": time.time(), **plan}
        self.store.put("installation", id, job)
        self.tasks[id] = asyncio.create_task(self._run(id, request, plan))
        return job

    async def _run(self, id: str, request: InstallRequest, plan: dict):
        job = self.store.get("installation", id)
        async with self.lock:
            job["status"] = "running"
            self.store.put("installation", id, job)
            work = self.store.root / "installations" / id
            work.mkdir(parents=True, exist_ok=True)
            try:
                if request.manager == "pip" and not Path(plan["argv"][0]).is_file():
                    result = await self.runner.process(
                        [
                            sys.executable,
                            "-m",
                            "venv",
                            str(self.store.root / "tools/python"),
                        ],
                        work,
                        self.runner.environment(Tool()),
                        timeout=180,
                    )
                    if not result.ok:
                        raise ValueError(
                            "Cannot create tool environment: " + result.stderr
                        )
                if request.manager == "apt":
                    socket = os.environ["AGENTICAI_INSTALLER_SOCKET"]
                    token = (
                        Path(os.environ["AGENTICAI_INSTALLER_TOKEN_FILE"])
                        .read_text()
                        .strip()
                    )
                    async with httpx.AsyncClient(
                        transport=httpx.AsyncHTTPTransport(uds=socket), timeout=900
                    ) as client:
                        response = await client.post(
                            "http://installer/install",
                            headers={"X-Installer-Token": token},
                            json=request.model_dump(),
                        )
                        response.raise_for_status()
                        result_data = response.json()
                else:
                    timeout = 900
                    if request.manager == "recipe":
                        timeout = Recipe.model_validate(
                            self.store.get("recipe", request.recipe_id)
                        ).timeout
                    result = await self.runner.process(
                        plan["argv"],
                        work,
                        self.runner.environment(Tool()),
                        timeout=timeout,
                        max_output=50000,
                    )
                    result_data = result.model_dump()
                job.update(
                    status="completed" if result_data["ok"] else "failed",
                    result=result_data,
                )
                if result_data["ok"]:
                    resolved = (
                        result_data.get("data", {}).get("resolved_version", "")
                        if isinstance(result_data.get("data"), dict)
                        else ""
                    )
                    resolved = resolved or await self._resolved_version(request, work)
                    job["resolved_version"] = resolved
                    key = request.manager + ":" + request.package
                    if request.action == "remove":
                        self.store.delete("installed_tool", key)
                    else:
                        self.store.put(
                            "installed_tool",
                            key,
                            {
                                **request.model_dump(),
                                "resolved_version": resolved,
                                "installed_at": time.time(),
                            },
                        )
            except asyncio.CancelledError:
                job.update(
                    status="interrupted",
                    error="Application stopped during installation",
                )
                raise
            except Exception as exc:
                job.update(status="failed", error=redact(str(exc)))
            finally:
                job["finished"] = time.time()
                self.store.put("installation", id, redact(job))
                self.tasks.pop(id, None)

    async def _resolved_version(self, request: InstallRequest, work: Path) -> str:
        if request.manager == "pip":
            python = (
                self.store.root
                / "tools/python"
                / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            )
            result = await self.runner.process(
                [str(python), "-m", "pip", "show", request.package],
                work,
                self.runner.environment(Tool()),
                timeout=30,
            )
            match = re.search(r"^Version: (.+)$", result.stdout, re.M)
            return match.group(1).strip() if match else request.version
        if request.manager == "npm":
            try:
                name = request.package.split("/")
                base = (
                    self.store.root
                    / "tools/npm"
                    / ("node_modules" if os.name == "nt" else "lib/node_modules")
                )
                return json.loads(base.joinpath(*name, "package.json").read_text())[
                    "version"
                ]
            except (OSError, KeyError, ValueError):
                pass
        if request.manager == "winget" and request.action != "remove":
            result = await self.runner.process(
                [
                    shutil.which("winget") or "winget",
                    "list",
                    "--id",
                    request.package,
                    "--exact",
                    "--disable-interactivity",
                ],
                work,
                self.runner.environment(Tool()),
                timeout=30,
            )
            for line in result.stdout.splitlines():
                tokens = line.split()
                if request.package in tokens:
                    index = tokens.index(request.package)
                    if index + 1 < len(tokens):
                        return tokens[index + 1]
        return request.version

    def manifest(self):
        return {"schema_version": 1, "tools": self.store.list("installed_tool")}

    def docker_recipe(self) -> str:
        packages = [
            x["package"]
            + (
                "=" + (x.get("resolved_version") or x.get("version"))
                if x.get("resolved_version") or x.get("version")
                else ""
            )
            for x in self.store.list("installed_tool")
            if x["manager"] == "apt"
        ]
        return (
            "FROM agenticai-studio:latest\nUSER root\n"
            + (
                "RUN apt-get update && apt-get install -y --no-install-recommends "
                + " ".join(packages)
                + " && rm -rf /var/lib/apt/lists/*\n"
                if packages
                else "# No additional system packages recorded.\n"
            )
            + "# The entrypoint starts the installer helper, then drops the app to UID 1000.\n"
        )

    async def close(self):
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
