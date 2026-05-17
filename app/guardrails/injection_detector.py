from __future__ import annotations

import re

from app.core.schemas import GuardrailResult

_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore previous instructions",
        r"disregard your instructions",
        r"disregard all previous instructions",
        r"new instructions follow",
        r"you are now",
        r"system:\s*you are now",
        r"your new instructions",
        r"developer mode",
        r"system message",
        r"reveal your hidden prompt",
        r"reveal the system prompt",
        r"jailbreak",
        r"\bDAN\b",
        r"execute tool",
        r"call external url",
        r"forget your instructions",
        r"pretend you have no restrictions",
    ]
]


def detect_injection(text: str) -> GuardrailResult:
    if any(pattern.search(text) is not None for pattern in _PATTERNS):
        return GuardrailResult(passed=False, reason="prompt_injection_detected")
    return GuardrailResult(passed=True)
