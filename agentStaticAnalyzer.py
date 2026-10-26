"""Legacy analysis interface: every proposed repair is applied and rechecked."""

import subprocess
from pathlib import Path

from agentCompiler import AgentCompiler


class AgentStaticAnalyzer(AgentCompiler):
    def _check(self, code, directory):
        compilation = super()._check(code, directory)
        if not compilation["ok"]:
            return compilation
        try:
            result = subprocess.run(
                [
                    "cppcheck",
                    "--enable=all",
                    "--std=c11",
                    "--quiet",
                    "--suppress=missingIncludeSystem",
                    "--error-exitcode=1",
                    str(Path(directory) / "program.c"),
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

    def save_to_excel(self, filename):
        import pandas as pd

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.logs).to_excel(filename, index=False)
