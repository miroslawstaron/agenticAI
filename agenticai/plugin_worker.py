"""Subprocess protocol for installed, trusted Python tool plugins."""

import asyncio
import importlib.metadata
import inspect
import json
import sys
from pathlib import Path


def main():
    request = json.load(sys.stdin)
    entries = {
        ep.name: ep for ep in importlib.metadata.entry_points(group="agenticai.tools")
    }
    plugin = entries[request["plugin"]].load()
    execute = getattr(plugin, "execute", plugin)
    result = execute(request["arguments"], Path(request["workspace"]))
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
