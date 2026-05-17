from app.core.schemas import Citation
from app.evaluation.metrics import (
    citation_validity_v0,
    classify_failure,
    context_recall_v0,
    keyword_overlap_v0,
    retrieval_hit_v0,
)
from app.retrieval.retriever import ScoredChunk


def citation() -> Citation:
    return Citation(
        index=1,
        chunk_id="c",
        document_id="d",
        source_filename="p",
        snippet="s",
        score=1.0,
    )


def chunk(text: str) -> ScoredChunk:
    return ScoredChunk(
        chunk_id="c",
        document_id="d",
        text=text,
        score=1.0,
        namespace="n",
        source_filename="p",
        page_start=1,
        page_end=1,
    )


def test_metric_functions() -> None:
    assert citation_validity_v0("MFA is required [1].", [citation()]) == 1.0
    assert citation_validity_v0("MFA is required.", [citation()]) == 0.0
    assert keyword_overlap_v0("MFA is required", "MFA is required") == 1.0
    assert context_recall_v0(["MFA required"], [chunk("MFA required for systems")]) == 1.0
    assert retrieval_hit_v0(["MFA required"], [chunk("MFA required for systems")]) is True


def test_failure_classifier() -> None:
    assert classify_failure(0.0, 1.0, 1.0) == "invalid_citation"
    assert classify_failure(1.0, 1.0, 0.1) == "insufficient_context"
    assert classify_failure(1.0, 0.1, 1.0) == "hallucination_risk"
    assert classify_failure(1.0, 0.6, 1.0) == "off_topic"
    assert classify_failure(1.0, 1.0, 1.0) == "passed"
