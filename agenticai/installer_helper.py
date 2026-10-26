"""Container-only privileged APT helper, reachable over a local Unix socket.

No arbitrary command, repository-editing, or host Docker API endpoint is exposed.
"""

import asyncio
import os
import re
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from .models import InstallRequest
from .tools import ToolRunner

app = FastAPI(docs_url=None, openapi_url=None)
lock = asyncio.Lock()


@app.post("/install")
async def install(request: Request):
    token = Path(os.environ["AGENTICAI_INSTALLER_TOKEN_FILE"]).read_text().strip()
    if not secrets.compare_digest(request.headers.get("X-Installer-Token", ""), token):
        raise HTTPException(403, "Invalid installer session")
    body = InstallRequest.model_validate(await request.json())
    if (
        body.manager != "apt"
        or body.source
        or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?", body.package)
    ):
        raise HTTPException(422, "Only Debian package operations are supported")
    if body.version and not re.fullmatch(r"[A-Za-z0-9:.+~_-]+", body.version):
        raise HTTPException(422, "Invalid Debian version")
    # Root logs are placed outside agent-writable workspaces, preventing symlink races.
    work = Path("/run/agenticai-installer")
    work.mkdir(mode=0o700, exist_ok=True)
    runner = ToolRunner(work, 1)
    env = {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "DEBIAN_FRONTEND": "noninteractive",
        "HOME": "/root",
    }
    async with lock:
        if body.action != "remove":
            update = await runner.process(
                ["apt-get", "update"], work, env, timeout=300, max_output=50000
            )
            if not update.ok:
                return update.model_dump()
        argv = [
            "apt-get",
            "remove" if body.action == "remove" else "install",
            "--yes",
            "--no-install-recommends",
            body.package
            + ("=" + body.version if body.version and body.action != "remove" else ""),
        ]
        result = await runner.process(argv, work, env, timeout=600, max_output=50000)
        result.artifacts = []
        if result.ok and body.action != "remove":
            probe = await runner.process(
                ["dpkg-query", "-W", "-f=${Version}", body.package],
                work,
                env,
                timeout=30,
            )
            result.data = {"resolved_version": probe.stdout.strip()}
        return result.model_dump()
