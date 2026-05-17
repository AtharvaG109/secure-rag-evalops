from __future__ import annotations

import re

from app.core.schemas import Citation
from app.retrieval.citations import CitationValidationError, validate_citations
from app.retrieval.retriever import ScoredChunk

_STOPWORDS = {"a", "an", "and", "are", "for", "is", "of", "the", "to"}
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(text)
        if token.lower() not in _STOPWORDS
    }


def citation_validity_v0(answer: str, citations: list[Citation]) -> float:
    try:
        validate_citations(answer, citations)
    except CitationValidationError:
        return 0.0
    return 1.0


def keyword_overlap_v0(generated: str, expected: str) -> float:
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return 1.0
    return len(_tokens(generated) & expected_tokens) / len(expected_tokens)


def context_recall_v0(
    ground_truth_contexts: list[str],
    retrieved_chunks: list[ScoredChunk],
) -> float:
    truth_tokens = set().union(*(_tokens(context) for context in ground_truth_contexts))
    if not truth_tokens:
        return 1.0
    retrieved_tokens = set().union(*(_tokens(chunk.text) for chunk in retrieved_chunks))
    return len(truth_tokens & retrieved_tokens) / len(truth_tokens)


def retrieval_hit_v0(
    ground_truth_contexts: list[str],
    retrieved_chunks: list[ScoredChunk],
) -> bool:
    return context_recall_v0(ground_truth_contexts, retrieved_chunks) > 0.0


def classify_failure(citation_v: float, keyword_v: float, context_v: float) -> str:
    if citation_v < 1.0:
        return "invalid_citation"
    if context_v < 0.5:
        return "insufficient_context"
    if keyword_v < 0.5 and context_v >= 0.5:
        return "hallucination_risk"
    if keyword_v < 0.75:
        return "off_topic"
    return "passed"
