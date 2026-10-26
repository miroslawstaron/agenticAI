"""Run this script with a clean environment containing only the release wheel."""

import asyncio
import json
import subprocess
import sys
import tempfile
from importlib.resources import files
from pathlib import Path

import httpx

import agenticai
from agenticai.api import create_app


async def verify():
    root = files("agenticai")
    assert root.joinpath("static/index.html").is_file()
    assert root.joinpath("static/tutorial/index.html").is_file()
    assert root.joinpath("docs/architecture.md").is_file()
    assert "site-packages" in str(root), root
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Path(directory) / "data")
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://localhost"
            ) as client:
                assert (await client.get("/")).status_code == 200
                assert (await client.get("/tutorial/")).status_code == 200
                token = (await client.get("/api/v1/session")).json()["token"]
                client.headers["X-Studio-Token"] = token
                network = (await client.get("/api/v1/networks/autonomous-team")).json()
                response = await client.post(
                    "/api/v1/runs",
                    json={"network": network, "prompt": "Verify installed release"},
                )
                id = response.json()["id"]
                run = app.state.manager.runs[id]
                await run.task
                details = (await client.get("/api/v1/runs/" + id)).json()
                assert details["status"] == "completed", details
                assert len(details["current_network"]["agents"]) == 2
                assert (
                    await client.get("/api/v1/runs/" + id + "/export/json")
                ).status_code == 200
        sample = root.joinpath("examples/designer-programmer.json")
        command = subprocess.run(
            [
                sys.executable,
                "-m",
                "agenticai",
                "run",
                str(sample),
                "--data",
                str(Path(directory) / "cli"),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        assert "completed" in command.stdout
    return {
        "status": "passed",
        "version": agenticai.__version__,
        "installed_location": str(root),
        "checks": [
            "wheel assets, docs and tutorial present",
            "local API and demo autonomy",
            "JSON export",
            "installed CLI workflow",
            "saved initial task and Programmer/Designer feedback workflow",
        ],
    }


if __name__ == "__main__":
    report = asyncio.run(verify())
    print(json.dumps(report, indent=2))
