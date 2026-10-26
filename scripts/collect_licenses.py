"""Include notices for the frontend's installed production dependency graph."""

import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
modules = root / "frontend/node_modules"
target = root / "agenticai/static/licenses"
target.mkdir(parents=True, exist_ok=True)
queue = list(json.loads((root / "frontend/package.json").read_text())["dependencies"])
seen = set()
rows = []
while queue:
    name = queue.pop()
    if name in seen:
        continue
    seen.add(name)
    package = modules / name
    if not (package / "package.json").is_file():
        continue
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    queue.extend(metadata.get("dependencies", {}))
    notices = []
    for path in package.iterdir():
        if path.is_file() and path.name.lower().startswith(
            ("license", "licence", "copying", "notice")
        ):
            filename = name.replace("/", "_").replace("@", "") + "-" + path.name
            shutil.copyfile(path, target / filename)
            notices.append(filename)
    rows.append(
        (
            name,
            metadata.get("version", ""),
            metadata.get("license", "See package notices"),
            ", ".join(notices),
        )
    )
text = "# Frontend third-party notices\n\nThese libraries are distributed with the compiled interface and tutorial. Their original notices are included alongside this file.\n\n| Package | Version | License | Notice files |\n|---|---|---|---|\n"
text += (
    "\n".join("| " + " | ".join(map(str, row)) + " |" for row in sorted(rows)) + "\n"
)
(target / "THIRD_PARTY_NOTICES.md").write_text(text, encoding="utf-8")
print(f"Collected notices for {len(rows)} production dependencies")
