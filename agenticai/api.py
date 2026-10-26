"""Local single-user API and same-origin web application."""

from __future__ import annotations

import asyncio
import base64
import binascii
import csv
import html
import io
import ipaddress
import json
import os
import secrets
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .examples import seed
from .installations import Installations
from .models import (
    Agent,
    InstallRequest,
    Network,
    Provider,
    Recipe,
    RunRequest,
    Tool,
    identifier,
)
from .runtime import Manager
from .security import redact, register_references
from .store import Store
from .tools import ToolRunner, resolve_executable

PACKAGE = Path(__file__).parent
TERMINAL = {"completed", "failed", "cancelled", "limited", "interrupted"}


def acquire_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    file = (root / "studio.lock").open("a+b")
    if file.tell() == 0:
        file.write(b"0")
        file.flush()
    file.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        file.close()
        raise RuntimeError(
            "This data directory is already open. Use one server worker, or choose a different --data directory."
        ) from None
    return file


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    root = Path(
        data_dir or os.getenv("AGENTICAI_DATA", Path.home() / ".agenticai")
    ).resolve()
    session_token = secrets.token_urlsafe(32)
    remote_password = os.getenv("AGENTICAI_REMOTE_PASSWORD", "")
    remote_username = os.getenv("AGENTICAI_REMOTE_USER", "studio")

    @asynccontextmanager
    async def lifespan(app):
        lock = acquire_lock(root)
        store = Store(root)
        seed(store)
        app.state.store = store
        app.state.manager = Manager(store)
        app.state.runner = ToolRunner(root)
        app.state.installations = Installations(store, app.state.runner)
        for provider in store.list("provider"):
            register_references(provider.get("api_key_env", ""))
        for tool in store.list("tool"):
            register_references(*tool.get("env", {}).values())
        try:
            yield
        finally:
            await app.state.installations.close()
            await app.state.manager.close()
            store.close()
            lock.close()

    app = FastAPI(title="AgenticAI Studio", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "[::1]",
            "testserver",
            *filter(None, os.getenv("AGENTICAI_ALLOWED_HOSTS", "").split(",")),
        ],
    )

    @app.middleware("http")
    async def local_session(request: Request, call_next):
        peer = request.client.host if request.client else ""
        try:
            address = ipaddress.ip_address(peer)
            local_peer = address.is_loopback or bool(
                getattr(address, "ipv4_mapped", None)
                and address.ipv4_mapped.is_loopback
            )
        except ValueError:
            local_peer = False
        # Docker Desktop can relay requests through a loopback peer. Only the
        # explicit local URL is exempt from login, rather than every such relay.
        local_host = request.url.hostname in {"localhost", "127.0.0.1", "::1"}
        if remote_password and not (local_peer and local_host):
            authorization = request.headers.get("authorization", "")
            authenticated = False
            try:
                scheme, encoded = authorization.split(" ", 1)
                username, password = (
                    base64.b64decode(encoded, validate=True)
                    .decode("utf-8")
                    .split(":", 1)
                )
                authenticated = (
                    scheme.lower() == "basic"
                    and secrets.compare_digest(
                        username.encode(), remote_username.encode()
                    )
                    and secrets.compare_digest(
                        password.encode(), remote_password.encode()
                    )
                )
            except (ValueError, UnicodeDecodeError, binascii.Error):
                pass
            if not authenticated:
                return Response(
                    "Remote access requires your Studio login.",
                    status_code=401,
                    headers={
                        "WWW-Authenticate": 'Basic realm="AgenticAI Studio", charset="UTF-8"',
                        "Cache-Control": "no-store",
                    },
                )
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return Response(
                    "Cross-origin requests are not allowed", status_code=403
                )
            supplied = request.headers.get("X-Studio-Token", "")
            if not secrets.compare_digest(supplied, session_token):
                return Response(
                    "Missing or invalid local session token",
                    status_code=403,
                    headers={"X-Studio-Session": "renew", "Cache-Control": "no-store"},
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = (
            "SAMEORIGIN" if request.url.path.startswith("/tutorial/") else "DENY"
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": redact(str(exc))}, status_code=422)

    @app.get("/api/v1/session")
    async def session(response: Response):
        response.headers["Cache-Control"] = "no-store"
        return {
            "token": session_token,
            "environment": "container" if os.getenv("AGENTICAI_CONTAINER") else "host",
            "platform": sys.platform,
            "data_dir": str(root),
            "version": "1.0.0",
            "external_access": bool(remote_password),
        }

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    def store() -> Store:
        return app.state.store

    def get(kind: str, id: str):
        value = store().get(kind, id)
        if value is None:
            raise HTTPException(404, "Not found")
        return value

    def active_run(id):
        run = app.state.manager.runs.get(id)
        if run is None or run.task.done():
            raise HTTPException(409, "Run is not active")
        return run

    @app.get("/api/v1/providers")
    async def providers():
        return store().list("provider")

    @app.put("/api/v1/providers/{id}")
    async def put_provider(id: str, provider: Provider):
        if id != provider.id:
            raise HTTPException(422, "Path and provider id differ")
        register_references(provider.api_key_env)
        return store().put("provider", id, provider)

    @app.delete("/api/v1/providers/{id}")
    async def delete_provider(id: str):
        store().delete("provider", id)
        return {"ok": True}

    @app.post("/api/v1/providers/{id}/test")
    async def test_provider(id: str, request: Request):
        provider = Provider.model_validate(get("provider", id))
        body = await request.json()
        definitions = (
            [
                {
                    "type": "function",
                    "function": {
                        "name": "connection_probe",
                        "description": "Verify tool calling",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]
            if provider.supports_tools
            else []
        )
        result = await app.state.manager.transport.complete(
            provider,
            Agent(
                name="Connection test", model=body.get("model", "demo"), max_tokens=128
            ),
            [
                {
                    "role": "user",
                    "content": "Call connection_probe if available, otherwise say connected.",
                }
            ],
            definitions,
        )
        return {
            "ok": True,
            "tools_verified": bool(result["message"].get("tool_calls"))
            or provider.kind == "demo",
            **redact(result),
        }

    @app.post("/api/v1/providers/{id}/probe")
    async def probe_provider(id: str, request: Request):
        data = await request.json()
        provider = Provider.model_validate(get("provider", id))
        result = await app.state.manager.transport.complete(
            provider,
            Agent(model=data.get("model", "demo"), max_tokens=128),
            [{"role": "user", "content": "Say connected."}],
        )
        return {"ok": True, **redact(result)}

    @app.get("/api/v1/providers/{id}/models")
    async def list_models(id: str):
        provider = Provider.model_validate(get("provider", id))
        if provider.kind == "demo":
            return ["demo"]
        key = os.getenv(provider.api_key_env, "")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        endpoint = provider.endpoint.removesuffix("/chat/completions") + "/models"
        try:
            response = await app.state.manager.transport.client.get(
                endpoint, headers=headers, timeout=min(provider.timeout, 15)
            )
            response.raise_for_status()
            return [m["id"] for m in response.json()["data"]]
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise HTTPException(
                422, "Model discovery unavailable; enter the model name manually"
            ) from None

    @app.get("/api/v1/agents")
    async def agents():
        return store().list("agent")

    @app.put("/api/v1/agents/{id}")
    async def put_agent(id: str, agent: Agent):
        if id != agent.id:
            raise ValueError("Path and agent id differ")
        return store().put("agent", id, agent)

    @app.delete("/api/v1/agents/{id}")
    async def delete_agent(id: str):
        store().delete("agent", id)
        return {"ok": True}

    @app.get("/api/v1/networks")
    async def networks():
        return store().list("network")

    @app.get("/api/v1/networks/{id}")
    async def network(id: str):
        return get("network", id)

    @app.put("/api/v1/networks/{id}")
    async def put_network(id: str, network: Network):
        if id != network.id:
            raise ValueError("Path and network id differ")
        return store().put("network", id, network)

    @app.delete("/api/v1/networks/{id}")
    async def delete_network(id: str):
        store().delete("network", id)
        return {"ok": True}

    @app.post("/api/v1/networks/validate")
    async def validate_network(network: Network):
        return app.state.manager.validate(network)

    @app.get("/api/v1/tools")
    async def tools():
        return store().list("tool")

    @app.get("/api/v1/plugins")
    async def plugins():
        return app.state.runner.plugin_metadata()

    @app.put("/api/v1/tools/{id}")
    async def put_tool(id: str, tool: Tool):
        if id != tool.id:
            raise ValueError("Path and tool id differ")
        register_references(*tool.env.values())
        return store().put("tool", id, tool)

    @app.delete("/api/v1/tools/{id}")
    async def delete_tool(id: str):
        store().delete("tool", id)
        return {"ok": True}

    @app.post("/api/v1/tools/{id}/test")
    async def test_tool(id: str, request: Request):
        tool = Tool.model_validate(get("tool", id))
        arguments = await request.json()
        result = await app.state.runner.execute(
            tool, arguments, root / "tool-tests" / identifier()
        )
        return result.model_dump()

    @app.get("/api/v1/tools/{id}/availability")
    async def availability(id: str):
        tool = Tool.model_validate(get("tool", id))
        executable = tool.executable or {
            "compiler": "gcc",
            "analyzer": "cppcheck",
            "shell": "powershell" if os.name == "nt" else "bash",
        }.get(tool.kind, "")
        if tool.kind == "python":
            return {"available": tool.plugin in app.state.runner.plugins}
        try:
            env = app.state.runner.environment(tool)
            resolved = (
                sys.executable
                if executable in ("python", "python3", "@python")
                else shutil.which(executable, path=env["PATH"])
                or resolve_executable(executable)
            )
            probe = tool.model_copy(
                update={
                    "kind": "cli",
                    "executable": resolved,
                    "args": tool.version_args,
                    "stdin": "",
                    "artifacts": [],
                    "input_schema": {"type": "object"},
                    "timeout": 10,
                    "output_format": "text",
                }
            )
            result = await app.state.runner.execute(
                probe, {}, root / "tool-tests" / identifier()
            )
            return {
                "available": True,
                "executable": resolved,
                "version": result.stdout or result.stderr,
                "version_check_ok": result.ok,
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"available": False, "error": str(exc)}

    @app.get("/api/v1/installations")
    async def installations():
        return store().list("installation")

    @app.get("/api/v1/installations/manifest")
    async def installation_manifest():
        return app.state.installations.manifest()

    @app.get("/api/v1/installations/dockerfile")
    async def installation_dockerfile():
        return Response(
            app.state.installations.docker_recipe(), media_type="text/plain"
        )

    @app.post("/api/v1/installations/preview")
    async def preview_installation(request: InstallRequest):
        return app.state.installations.preview(request)

    @app.post("/api/v1/installations/restore-preview")
    async def restore_preview(request: Request):
        body = await request.json()
        if body.get("schema_version") != 1 or not isinstance(body.get("tools"), list):
            raise ValueError("Expected a version 1 installation manifest")
        plans = []
        for item in body["tools"]:
            fields = {
                key: item[key]
                for key in ("manager", "package", "source", "recipe_id")
                if key in item
            }
            fields.update(
                action="install",
                version=item.get("resolved_version") or item.get("version", ""),
            )
            plans.append(
                app.state.installations.preview(InstallRequest.model_validate(fields))
            )
        return plans

    @app.post("/api/v1/installations")
    async def start_installation(request: Request):
        body = await request.json()
        return app.state.installations.start(
            InstallRequest.model_validate(body["request"]), body.get("confirmation", "")
        )

    @app.get("/api/v1/recipes")
    async def recipes():
        return store().list("recipe")

    @app.put("/api/v1/recipes/{id}")
    async def put_recipe(id: str, recipe: Recipe):
        if id != recipe.id:
            raise ValueError("Path and recipe id differ")
        return store().put("recipe", id, recipe)

    @app.post("/api/v1/runs")
    async def start_run(request: RunRequest):
        run = app.state.manager.start(request.network, request.prompt)
        return {"id": run.id, "status": "queued"}

    @app.get("/api/v1/runs")
    async def runs():
        return store().runs()

    @app.get("/api/v1/runs/{id}")
    async def run_details(id: str):
        run = store().run(id)
        if run is None:
            raise HTTPException(404, "Run not found")
        active = app.state.manager.runs.get(id)
        run["current_network"] = (
            active.network.model_dump()
            if active
            else store().latest_network(id) or run["snapshot"]["network"]
        )
        run["messages"] = store().messages(id)
        run["pending_human"] = list(active.human) if active else []
        return run

    @app.post("/api/v1/runs/{id}/control/{action}")
    async def control(id: str, action: str):
        active_run(id).control(action)
        return {"ok": True}

    @app.post("/api/v1/runs/{id}/human/{agent_id}")
    async def human_response(id: str, agent_id: str, request: Request):
        body = await request.json()
        text = body.get("message")
        if not isinstance(text, str) or len(text) > 1000000:
            raise ValueError("Provide a text message of at most one million characters")
        active_run(id).respond(agent_id, text)
        return {"ok": True}

    @app.get("/api/v1/runs/{id}/events")
    async def events(id: str, request: Request, after: int = 0, stream: bool = True):
        if store().run(id) is None:
            raise HTTPException(404, "Run not found")
        try:
            cursor = max(after, int(request.headers.get("Last-Event-ID", "0")))
        except ValueError:
            raise HTTPException(422, "Invalid event cursor") from None
        if not stream:
            return store().events(id, cursor)

        async def generate():
            nonlocal cursor
            ticks = 0
            while not await request.is_disconnected():
                rows = store().events(id, cursor)
                for row in rows:
                    cursor = row["seq"]
                    yield f"id: {cursor}\ndata: {json.dumps(row)}\n\n"
                if not rows and store().run(id)["status"] in TERMINAL:
                    yield "event: end\ndata: {}\n\n"
                    return
                ticks += 1
                if ticks % 30 == 0:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.2)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/v1/runs/{id}/export/{format}")
    async def export(id: str, format: str):
        run = store().run(id)
        if run is None:
            raise HTTPException(404, "Run not found")
        messages = store().messages(id)
        if format == "json":
            events, cursor = [], 0
            while page := store().events(id, cursor):
                events.extend(page)
                cursor = page[-1]["seq"]
            active = app.state.manager.runs.get(id)
            current = (
                active.network.model_dump()
                if active
                else store().latest_network(id) or run["snapshot"]["network"]
            )
            payload = json.dumps(
                {
                    **run,
                    "current_network": current,
                    "messages": messages,
                    "events": events,
                },
                indent=2,
                ensure_ascii=False,
            )
            return Response(
                payload,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="run-{id}.json"'
                },
            )
        if format == "csv":
            output = io.StringIO(newline="")
            writer = csv.DictWriter(
                output,
                fieldnames=["seq", "agent_id", "role", "content"],
                extrasaction="ignore",
            )
            writer.writeheader()
            for message in messages:
                # Spreadsheet formula injection protection for CSV consumers.
                writer.writerow(
                    {
                        key: (
                            "'" + str(value)
                            if isinstance(value, str)
                            and value.startswith(("=", "+", "-", "@"))
                            else value
                        )
                        for key, value in message.items()
                    }
                )
            return Response(
                output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="run-{id}.csv"'},
            )
        if format == "html":
            body = "".join(
                f"<article><h2>{html.escape(m['agent_id'])} / {html.escape(m['role'])}</h2><pre>{html.escape(str(m.get('content') or m.get('tool_calls') or ''))}</pre></article>"
                for m in messages
            )
            return HTMLResponse(
                f'<!doctype html><meta charset="utf-8"><title>AgenticAI run {id}</title><style>body{{font:16px system-ui;max-width:1000px;margin:40px auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}article{{border-bottom:1px solid #ddd;padding:20px}}</style><h1>Run {id}</h1>{body}'
            )
        if format == "xlsx":
            try:
                import pandas as pd
            except ImportError:
                raise HTTPException(
                    422, "Install agenticai-studio[excel] for Excel exports"
                ) from None
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                pd.DataFrame(messages).map(
                    lambda value: (
                        "'" + value
                        if isinstance(value, str)
                        and value.startswith(("=", "+", "-", "@"))
                        else value
                    )
                ).to_excel(writer, index=False)
            return Response(
                output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="run-{id}.xlsx"'
                },
            )
        raise HTTPException(422, "Choose json, csv, html, or xlsx")

    @app.get("/api/v1/artifacts/{path:path}")
    async def artifact(path: str):
        candidate = (root / path).resolve()
        allowed = any(
            candidate.is_relative_to(root / folder)
            for folder in ("runs", "tool-tests", "installations")
        )
        if not allowed or not candidate.is_file() or candidate.is_symlink():
            raise HTTPException(404, "Artifact not found")
        return FileResponse(
            candidate, filename=candidate.name, media_type="application/octet-stream"
        )

    @app.get("/api/v1/docs")
    async def docs_list():
        return [p.name for p in (PACKAGE / "docs").glob("*.md")]

    @app.get("/api/v1/docs/{name}")
    async def docs_file(name: str):
        path = PACKAGE / "docs" / name
        if path.suffix != ".md" or path.name != name or not path.is_file():
            raise HTTPException(404, "Document not found")
        return Response(path.read_text(encoding="utf-8"), media_type="text/plain")

    static = PACKAGE / "static"
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="web")
    return app
