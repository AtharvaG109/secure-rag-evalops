import pytest

from app.core.schemas import Citation
from app.retrieval.citations import CitationValidationError, validate_citations


def citation(index: int) -> Citation:
    return Citation(
        index=index,
        chunk_id="c",
        document_id="d",
        source_filename="p.md",
        snippet="text",
        score=1.0,
    )


def test_validator_rejects_out_of_range_markers() -> None:
    with pytest.raises(CitationValidationError, match="out of range"):
        validate_citations("MFA is required [2].", [citation(1)])


def test_validator_rejects_factual_answer_without_citations() -> None:
    with pytest.raises(CitationValidationError, match="requires citations"):
        validate_citations("MFA is required.", [citation(1)])
