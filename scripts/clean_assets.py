"""Remove only stale generated asset files; preserve the bundled tutorial."""

import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
assets = (root / "agenticai/static/assets").resolve()
assert assets.is_relative_to(root)
index = (root / "agenticai/static/index.html").read_text(encoding="utf-8")
retained = set(re.findall(r'/assets/([^"\s]+)', index))
pending = list(retained)
while pending:
    name = pending.pop()
    path = assets / name
    if path.is_file() and path.suffix in (".js", ".css"):
        for child in re.findall(
            r'["\']\.?/?([A-Za-z0-9_-]+\.(?:js|css))["\']',
            path.read_text(encoding="utf-8"),
        ):
            if child not in retained:
                retained.add(child)
                pending.append(child)
removed = []
for path in assets.iterdir():
    if path.is_file() and path.suffix in (".js", ".css") and path.name not in retained:
        assert path.resolve().is_relative_to(assets)
        path.unlink()
        removed.append(path.name)
print({"removed_stale_assets": removed, "retained": sorted(retained)})
