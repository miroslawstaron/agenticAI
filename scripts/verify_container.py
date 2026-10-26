"""Exercise a real container, installers, derived image and volume recreation."""

import argparse
import json
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--image", default="agenticai-studio:latest")
parser.add_argument("--port", type=int, default=8878)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
suffix = uuid4().hex[:8]
name = "agenticai-test-" + suffix
volume = name + "-data"
derived = "agenticai-studio:test-" + suffix
url = f"http://127.0.0.1:{args.port}"
checks = []


def docker(*arguments):
    result = subprocess.run(
        ["docker", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def start(image):
    docker(
        "run",
        "-d",
        "--name",
        name,
        "-p",
        f"127.0.0.1:{args.port}:8765",
        "-v",
        f"{volume}:/data",
        image,
    )
    for _ in range(100):
        try:
            if httpx.get(url + "/health", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(docker("logs", name))


def install(client, manager, package):
    request = {"manager": manager, "package": package}
    preview = client.post("/api/v1/installations/preview", json=request)
    preview.raise_for_status()
    job = client.post(
        "/api/v1/installations",
        json={
            "request": preview.json()["request"],
            "confirmation": preview.json()["confirmation"],
        },
    )
    job.raise_for_status()
    id = job.json()["id"]
    for _ in range(1200):
        jobs = client.get("/api/v1/installations").json()
        current = next(job for job in jobs if job["id"] == id)
        if current["status"] not in ("queued", "running"):
            assert current["status"] == "completed", current
            checks.append(
                {
                    "installation": manager + ":" + package,
                    "version": current.get("resolved_version"),
                }
            )
            return current
        time.sleep(0.1)
    raise RuntimeError("Installation did not finish")


try:
    start(args.image)
    with httpx.Client(base_url=url, timeout=60) as client:
        client.headers["X-Studio-Token"] = client.get("/api/v1/session").json()["token"]
        assert client.get("/").status_code == 200
        assert client.get("/tutorial/").status_code == 200
        network = client.get("/api/v1/networks/compiler-analyzer").json()
        run = client.post(
            "/api/v1/runs",
            json={"network": network, "prompt": "Generate a C greeting program"},
        ).json()
        for _ in range(200):
            result = client.get("/api/v1/runs/" + run["id"]).json()
            if result["status"] in ("completed", "failed", "limited"):
                break
            time.sleep(0.05)
        assert result["status"] == "completed", result
        checks.append("C generation, GCC compilation, and cppcheck passed in Linux")
        tool = {
            "id": "identity",
            "name": "Identity",
            "kind": "shell",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        }
        client.put("/api/v1/tools/identity", json=tool).raise_for_status()
        result = client.post(
            "/api/v1/tools/identity/test",
            json={"command": 'printf hello | tr a-z A-Z; printf "\\n"; id -u'},
        ).json()
        assert result["ok"] and result["stdout"].strip() == "HELLO\n1000", result
        checks.append("Shell pipeline executed as unprivileged UID 1000")
        install(client, "pip", "ruff")
        install(client, "npm", "json5")
        install(client, "apt", "jq")
        for id, exe in [("ruff", "ruff"), ("json5", "json5"), ("jq", "jq")]:
            client.put(
                "/api/v1/tools/" + id,
                json={"id": id, "name": id, "executable": exe, "args": ["--version"]},
            ).raise_for_status()
            result = client.post("/api/v1/tools/" + id + "/test", json={}).json()
            assert result["ok"], result
        checks.append("Managed Python, npm and APT executables were callable by agents")
        manifest = client.get("/api/v1/installations/manifest").json()
        assert len(manifest["tools"]) == 3
        assert (
            client.post(
                "/api/v1/installations/restore-preview", json=manifest
            ).status_code
            == 200
        )
        recipe = client.get("/api/v1/installations/dockerfile").text
        assert "jq=" in recipe
        recipe = recipe.replace("FROM agenticai-studio:latest", "FROM " + args.image)
        path = root / ".build/Dockerfile.tools-test"
        path.write_text(recipe, encoding="utf-8")
        docker("build", "-t", derived, "-f", str(path), str(root))
    docker("stop", name)
    docker("rm", name)
    start(derived)
    with httpx.Client(base_url=url, timeout=30) as client:
        client.headers["X-Studio-Token"] = client.get("/api/v1/session").json()["token"]
        assert len(client.get("/api/v1/installations/manifest").json()["tools"]) == 3
        assert client.get("/api/v1/runs/" + run["id"]).json()["status"] == "completed"
        for id in ("ruff", "json5", "jq"):
            result = client.post("/api/v1/tools/" + id + "/test", json={}).json()
            assert result["ok"], result
        checks.append(
            "Container recreation retained runs, configurations, and managed environments; derived image restored pinned APT tool"
        )
    report = {"checks": checks, "image": args.image, "status": "passed"}
    (root / ".build/container-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
finally:
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    subprocess.run(["docker", "volume", "rm", volume], capture_output=True, check=False)
    subprocess.run(["docker", "image", "rm", derived], capture_output=True, check=False)
