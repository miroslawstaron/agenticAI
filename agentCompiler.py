"""Legacy compiler interface backed by isolated, checked subprocesses."""

import re
import subprocess
import tempfile
from pathlib import Path

from agent import AgentAI


def extract_c(code):
    match = re.search(r"```(?:c|C)\s*\n(.*?)```", code or "", re.S)
    return match.group(1).strip() if match else (code or "").strip()


class AgentCompiler(AgentAI):
    def __init__(
        self, server_address, model_name, trials, api_key="", max_tokens=16000
    ):
        super().__init__(
            server_address,
            model_name,
            "You are a C programmer. Return the complete corrected C program in a fenced code block.",
            max_tokens,
            api_key,
        )
        self.trials, self.temperature = trials, 0.0
        self.last_result = {"ok": False, "diagnostics": "Not run"}
        self.logs = []

    def _check(self, code, directory):
        source = Path(directory) / "program.c"
        source.write_text(code, encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    str(source),
                    "-o",
                    str(Path(directory) / "program.out"),
                    "-lm",
                ],
                capture_output=True,
                timeout=60,
            )
            return {
                "ok": result.returncode == 0,
                "diagnostics": result.stderr.decode("utf-8", "replace"),
                "exit_code": result.returncode,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "diagnostics": str(exc), "exit_code": None}

    def get_response(self, code):
        with (
            self._lock,
            tempfile.TemporaryDirectory(prefix="agenticai-c-") as directory,
        ):
            code = extract_c(code)
            if not code:
                self.last_result = {"ok": False, "diagnostics": "No code found"}
                return ""
            for attempt in range(self.trials + 1):
                self.last_result = self._check(code, directory)
                self.logs.append({"code": code, **self.last_result})
                if (
                    self.last_result["ok"]
                    or attempt == self.trials
                    or self.last_result.get("exit_code") is None
                ):
                    break
                repaired = super().get_response(
                    f"Fix this C program:\n```c\n{code}\n```\nDiagnostics:\n{self.last_result['diagnostics']}"
                )
                if not repaired:
                    break
                code = extract_c(repaired)
            return code
