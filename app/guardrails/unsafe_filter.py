from __future__ import annotations

import re

from app.core.schemas import GuardrailResult

_CATEGORY_PATTERNS = {
    "credential_extraction": re.compile(
        r"(steal|extract).*(password|credential|token)",
        re.IGNORECASE,
    ),
    "data_exfiltration": re.compile(r"(exfiltrate|send).*(customer|secret|data)", re.IGNORECASE),
    "system_abuse": re.compile(r"(disable|bypass).*(security|logging|controls)", re.IGNORECASE),
}


def filter_unsafe_query(query: str) -> GuardrailResult:
    for category, pattern in _CATEGORY_PATTERNS.items():
        if pattern.search(query) is not None:
            return GuardrailResult(passed=False, reason=f"unsafe_query_{category}")
    return GuardrailResult(passed=True)
