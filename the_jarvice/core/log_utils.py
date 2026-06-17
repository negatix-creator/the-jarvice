"""Log sanitization utilities for The Jarvice.

Masks sensitive fields (tokens, passwords, secrets) in log output
to prevent credential leakage.
"""

from __future__ import annotations

import re
from typing import Any

# Fields that should always be masked in log output
SENSITIVE_FIELDS = frozenset({
    "password", "token", "secret", "api_key", "apikey",
    "access_token", "refresh_token", "bearer", "authorization",
    "ic3_token", "bot_token", "credential",
})

# Patterns that look like tokens/secrets in strings
_TOKEN_PATTERNS = [
    re.compile(r"(Bearer\s+)([A-Za-z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(token[=:\s]+)([A-Za-z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(password[=:\s]+)(\S+)", re.IGNORECASE),
]


def mask_value(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value, showing only the last N characters.

    Args:
        value: The sensitive string to mask.
        visible_chars: Number of characters to show at the end.

    Returns:
        Masked string like '****abcd' or '****' if too short.
    """
    if not value or len(value) <= visible_chars:
        return "****"
    return f"****{value[-visible_chars:]}"


def sanitize_for_log(data: Any, max_depth: int = 5) -> Any:
    """Recursively sanitize a data structure for safe logging.

    Masks values of keys matching SENSITIVE_FIELDS and applies
    regex patterns to string values.

    Args:
        data: Any data structure (dict, list, str, etc.).
        max_depth: Maximum recursion depth.

    Returns:
        Sanitized copy of the data structure.
    """
    if max_depth <= 0:
        return "..."

    if isinstance(data, dict):
        return {
            k: mask_value(str(v)) if _is_sensitive_key(k) else sanitize_for_log(v, max_depth - 1)
            for k, v in data.items()
        }

    if isinstance(data, (list, tuple)):
        return [sanitize_for_log(item, max_depth - 1) for item in data]

    if isinstance(data, str):
        return _sanitize_string(data)

    return data


def _is_sensitive_key(key: str) -> bool:
    """Check if a dict key indicates a sensitive field."""
    key_lower = key.lower().replace("-", "_").replace(" ", "_")
    return key_lower in SENSITIVE_FIELDS or any(s in key_lower for s in ("token", "password", "secret", "api_key"))


def _sanitize_string(text: str) -> str:
    """Apply regex patterns to mask tokens/secrets in a string."""
    result = text
    for pattern in _TOKEN_PATTERNS:
        result = pattern.sub(lambda m: f"{m.group(1)}****", result)
    return result