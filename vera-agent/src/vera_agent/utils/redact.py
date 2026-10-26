"""Secret detection shared by every path that persists model or tool text (memories, traces)."""

from __future__ import annotations

import re
from typing import Any

SECRET_VALUE = re.compile(
    r"(?:api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*\S+|\bsk-[A-Za-z0-9_-]{12,}", re.IGNORECASE
)


def contains_secret(text: str) -> bool:
    return bool(SECRET_VALUE.search(text))


def redact_secrets(value: Any, limit: int = 2000) -> Any:
    """Return ``value`` with secret-looking substrings masked and long strings truncated.

    Dicts and lists are redacted recursively; other values are returned unchanged.
    """
    if isinstance(value, str):
        masked = SECRET_VALUE.sub("[REDACTED]", value)
        return masked if len(masked) <= limit else masked[:limit] + f"…[truncated {len(masked) - limit} chars]"
    if isinstance(value, dict):
        return {key: redact_secrets(item, limit) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item, limit) for item in value]
    return value
