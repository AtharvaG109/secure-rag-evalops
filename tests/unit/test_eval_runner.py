from typing import Any

import pytest

from app.core.schemas import Citation, EvalSample
from app.evaluation.runner import EvalRunner
from app.retrieval.generator import GenerationResult
from app.retrieval.retriever import RetrievalResult, ScoredChunk


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        return None


class FakeRetriever:
    def __init__(self) -> None:
        self.user_ids: list[str] = []

    async def retrieve(self, request: Any) -> RetrievalResult:
        self.user_ids.append(request.user_id)
        citation = Citation(
            index=1,
            chunk_id="c",
            document_id="d",
            source_filename="p",
            snippet="MFA required",
            score=1.0,
        )
        return RetrievalResult(
            context="[1] MFA required",
            citations=[citation],
            chunks=[
                ScoredChunk(
                    chunk_id="c",
                    document_id="d",
                    text="MFA required",
                    score=1.0,
                    namespace="n",
                    source_filename="p",
                    page_start=1,
                    page_end=1,
                )
            ],
            chunks_used=1,
            retrieval_latency_ms=1.0,
        )


class FakeGenerator:
    async def generate(self, _: str, __: str) -> GenerationResult:
        return GenerationResult(answer="MFA is required [1].", prompt_tokens=1, completion_tokens=1)


@pytest.mark.asyncio
async def test_eval_runner_uses_passed_in_user_id_and_writes_row() -> None:
    session = FakeSession()
    retriever = FakeRetriever()
    runner = EvalRunner(session, retriever, FakeGenerator())  # type: ignore[arg-type]
    sample = EvalSample(
        query="Is MFA required?",
        expected_answer="MFA is required.",
        ground_truth_contexts=["MFA required"],
        namespace="security-policy",
    )

    result = await runner.run_sample(sample, "run-1", "analyst-1")

    assert retriever.user_ids == ["analyst-1"]
    assert result.failure_type == "passed"
    assert session.added
