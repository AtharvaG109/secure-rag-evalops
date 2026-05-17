from __future__ import annotations

import re

from pydantic import BaseModel

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"\b(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


class RedactResult(BaseModel):
    text: str
    entities_found: list[str]
    count: int


def _luhn_valid(candidate: str) -> bool:
    digits = [int(char) for char in candidate if char.isdigit()]
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def redact_pii(text: str) -> RedactResult:
    entities: list[str] = []
    redacted = text
    for pattern, label in [(_EMAIL, "EMAIL"), (_PHONE, "PHONE"), (_SSN, "SSN")]:
        matches = pattern.findall(redacted)
        if matches:
            entities.extend([label] * len(matches))
            redacted = pattern.sub(f"[{label}]", redacted)

    def replace_card(match: re.Match[str]) -> str:
        candidate = match.group(0)
        if _luhn_valid(candidate):
            entities.append("CREDIT_CARD")
            return "[CREDIT_CARD]"
        return candidate

    redacted = _CARD_CANDIDATE.sub(replace_card, redacted)
    return RedactResult(text=redacted, entities_found=entities, count=len(entities))
