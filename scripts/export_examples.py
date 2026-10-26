"""Write portable demo networks and tool definitions from the application seed."""

import json
import tempfile
from pathlib import Path

from agenticai.examples import seed
from agenticai.store import Store

root = Path(__file__).resolve().parents[1]
target = root / "agenticai/examples"
target.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    store = Store(directory)
    seed(store)
    for network in store.list("network"):
        (target / (network["id"] + ".json")).write_text(
            json.dumps(network, indent=2), encoding="utf-8"
        )
    (target / "providers.json").write_text(
        json.dumps(store.list("provider"), indent=2), encoding="utf-8"
    )
    (target / "tools.json").write_text(
        json.dumps(store.list("tool"), indent=2), encoding="utf-8"
    )
    store.close()
print(f"Examples exported to {target}")
