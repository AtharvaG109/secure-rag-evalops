from __future__ import annotations

import re

from app.core.schemas import Citation

INSUFFICIENT_CONTEXT_ANSWER = (
    "I don't have enough information in the provided context to answer this question."
)
_MARKER_PATTERN = re.compile(r"\[(-?\d+)\]")
_FACTUAL_WORD_PATTERN = re.compile(
    r"\b(is|are|requires?|must|within|retained|uses?|has|have)\b",
    re.IGNORECASE,
)


class CitationValidationError(Exception):
    pass


def extract_citation_markers(answer: str) -> list[int]:
    return [int(match.group(1)) for match in _MARKER_PATTERN.finditer(answer)]


def validate_citations(answer: str, citations: list[Citation]) -> None:
    if answer.strip() == INSUFFICIENT_CONTEXT_ANSWER:
        return
    markers = extract_citation_markers(answer)
    if any(marker < 1 for marker in markers):
        raise CitationValidationError("citation marker must be positive")
    if any(marker > len(citations) for marker in markers):
        raise CitationValidationError("citation marker out of range")
    citation_indexes = [citation.index for citation in citations]
    if len(citation_indexes) != len(set(citation_indexes)):
        raise CitationValidationError("citation ambiguity exists")
    if _FACTUAL_WORD_PATTERN.search(answer) is not None and not markers:
        raise CitationValidationError("factual answer requires citations")
