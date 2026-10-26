"""Redact configured credentials before persistence or display."""

import os
import re
from typing import Any

_references: set[str] = set()


def register_references(*names: str):
    _references.update(n for n in names if n)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        names = _references | {
            k for k in os.environ if re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.I)
        }
        for name in names:
            secret = os.environ.get(name, "")
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value
    return value
