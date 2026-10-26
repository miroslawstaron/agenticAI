"""Bounded inspection of cloud-backed legacy files."""

import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [
    root / "requirements.txt",
    root / "LICENSE",
    *sorted((root / "test").glob("*.py")),
    root / "agentH.py",
    root / "main_human.py",
    root / "requirements/agent_reqs.py",
    root / "requirements/agent_3gpp.py",
]
report = []
for path in paths:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys;from pathlib import Path;print(Path(sys.argv[1]).read_text(encoding='utf-8'))",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=2,
        )
        report.append(
            {
                "path": str(path.relative_to(root)),
                "readable": result.returncode == 0,
                "content": result.stdout if result.returncode == 0 else "",
                "error": result.stderr.strip(),
            }
        )
    except subprocess.TimeoutExpired:
        report.append(
            {
                "path": str(path.relative_to(root)),
                "readable": False,
                "error": "Cloud file read exceeded 2 seconds; hydration unavailable",
            }
        )
target = root / ".build/cloud-inspection.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    json.dumps(
        [{k: v for k, v in item.items() if k != "content"} for item in report], indent=2
    )
)
