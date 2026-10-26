import argparse
import asyncio
import json
from pathlib import Path

from .models import Network


def main():
    parser = argparse.ArgumentParser(
        prog="agenticai", description="Local agent networks and tools"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Start the local web interface")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--data", type=Path, default=Path.home() / ".agenticai")
    serve.add_argument("--open", action="store_true", help="Open your browser")
    validate = sub.add_parser("validate", help="Validate a network JSON file")
    validate.add_argument("file", type=Path)
    run = sub.add_parser("run", help="Execute a network JSON file")
    run.add_argument("file", type=Path)
    run.add_argument("--prompt", help="Override the network's saved initial task")
    run.add_argument("--data", type=Path, default=Path.home() / ".agenticai")
    run.add_argument("--providers", type=Path, help="JSON array of provider profiles")
    run.add_argument("--tools", type=Path, help="JSON array of tool definitions")
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        from .api import create_app

        if args.open:
            import threading
            import webbrowser

            timer = threading.Timer(
                1.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")
            )
            timer.daemon = True
            timer.start()
        print(f"AgenticAI Studio: http://{args.host}:{args.port}")
        uvicorn.run(create_app(args.data), host=args.host, port=args.port, workers=1)
    elif args.command == "validate":
        try:
            network = Network.model_validate_json(args.file.read_text(encoding="utf-8"))
            print(f"Valid network: {network.name} ({len(network.agents)} nodes)")
            print("Provider/tool references are checked when starting a run.")
        except (ValueError, OSError) as exc:
            parser.exit(1, str(exc) + "\n")
    else:
        asyncio.run(run_file(args))


async def run_file(args):
    from .api import acquire_lock
    from .examples import seed
    from .models import Provider, Tool
    from .runtime import Manager
    from .store import Store

    lock = acquire_lock(args.data)
    store = Store(args.data)
    seed(store)
    manager = Manager(store)
    try:
        for attr, model, kind in (
            ("providers", Provider, "provider"),
            ("tools", Tool, "tool"),
        ):
            path = getattr(args, attr)
            if path:
                for body in json.loads(path.read_text(encoding="utf-8")):
                    value = model.model_validate(body)
                    store.put(kind, value.id, value)
        network = Network.model_validate_json(args.file.read_text(encoding="utf-8"))
        run = manager.start(network, args.prompt)
        cursor = 0
        while not run.task.done():
            for event in store.events(run.id, cursor):
                cursor = event["seq"]
                if event["kind"] == "human_input":
                    text = await asyncio.to_thread(
                        input,
                        f"{event['body']['agent_id']}: {event['body']['prompt']}\n> ",
                    )
                    run.respond(event["body"]["agent_id"], text)
                elif event["kind"] in ("agent_completed", "status", "error"):
                    print(json.dumps(event, ensure_ascii=False))
            await asyncio.sleep(0.1)
        await run.task
        print(json.dumps(store.run(run.id), ensure_ascii=False))
        if run.status != "completed":
            raise SystemExit(1)
    finally:
        await manager.close()
        store.close()
        lock.close()


if __name__ == "__main__":
    main()
