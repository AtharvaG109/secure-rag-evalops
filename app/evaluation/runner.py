from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import EvalResultORM, EvalRunORM
from app.core.schemas import EvalResult, EvalSample, QueryRequest
from app.core.settings import settings
from app.evaluation.dataset import load_jsonl_dataset
from app.evaluation.metrics import (
    citation_validity_v0,
    classify_failure,
    context_recall_v0,
    keyword_overlap_v0,
    retrieval_hit_v0,
)
from app.retrieval.generator import ResponseGenerator
from app.retrieval.retriever import RAGRetriever
from app.tracing.trace import trace_span


class EvalRunner:
    def __init__(
        self,
        session: AsyncSession,
        retriever: RAGRetriever,
        generator: ResponseGenerator,
    ) -> None:
        self._session = session
        self._retriever = retriever
        self._generator = generator

    async def run_sample(self, sample: EvalSample, run_id: str, user_id: str) -> EvalResult:
        async with trace_span("evaluation.run_sample"):
            return await self._run_sample(sample, run_id, user_id)

    async def _run_sample(self, sample: EvalSample, run_id: str, user_id: str) -> EvalResult:
        result = await self._evaluate_sample(sample, user_id)
        self._session.add(EvalResultORM(run_id=run_id, **result.model_dump()))
        await self._session.commit()
        return result

    async def _evaluate_sample(self, sample: EvalSample, user_id: str) -> EvalResult:
        retrieval = await self._retriever.retrieve(
            QueryRequest(
                query=sample.query,
                namespace=sample.namespace,
                user_id=user_id,
                top_k=settings.TOP_K,
            )
        )
        generation = await self._generator.generate(sample.query, retrieval.context)
        citation_v = citation_validity_v0(generation.answer, retrieval.citations)
        keyword_v = keyword_overlap_v0(generation.answer, sample.expected_answer)
        context_v = context_recall_v0(sample.ground_truth_contexts, retrieval.chunks)
        hit = retrieval_hit_v0(sample.ground_truth_contexts, retrieval.chunks)
        failure_type = classify_failure(citation_v, keyword_v, context_v)
        return EvalResult(
            query=sample.query,
            expected_answer=sample.expected_answer,
            generated_answer=generation.answer,
            citation_validity_v0=citation_v,
            keyword_overlap_v0=keyword_v,
            context_recall_v0=context_v,
            retrieval_hit_v0=hit,
            failure_type=failure_type,
            latency_ms=retrieval.retrieval_latency_ms,
        )

    async def run_batch(
        self,
        dataset_path: str,
        pipeline_version: str,
        namespace: str,
        user_id: str,
    ) -> EvalRunORM:
        run = EvalRunORM(pipeline_version=pipeline_version, namespace=namespace, status="running")
        self._session.add(run)
        await self._session.flush()
        samples = load_jsonl_dataset(dataset_path)
        semaphore = asyncio.Semaphore(5)

        async def run_with_limit(sample: EvalSample) -> EvalResult:
            async with semaphore:
                return await self._evaluate_sample(sample, user_id)

        results = await asyncio.gather(*(run_with_limit(sample) for sample in samples))
        self._session.add_all(
            EvalResultORM(run_id=run.id, **result.model_dump()) for result in results
        )
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        await self._session.commit()
        return run

    async def summary_stats(self, run_id: str) -> dict[str, Any]:
        results = list(
            await self._session.scalars(select(EvalResultORM).where(EvalResultORM.run_id == run_id))
        )
        if not results:
            return {
                "sample_count": 0,
                "citation_validity_v0": 0.0,
                "keyword_overlap_v0": 0.0,
                "context_recall_v0": 0.0,
                "retrieval_hit_rate": 0.0,
                "failure_counts": {},
            }
        failure_counts: dict[str, int] = {}
        for result in results:
            failure_counts[result.failure_type] = failure_counts.get(result.failure_type, 0) + 1
        count = len(results)
        return {
            "sample_count": count,
            "citation_validity_v0": sum(result.citation_validity_v0 for result in results) / count,
            "keyword_overlap_v0": sum(result.keyword_overlap_v0 for result in results) / count,
            "context_recall_v0": sum(result.context_recall_v0 for result in results) / count,
            "retrieval_hit_rate": sum(1 for result in results if result.retrieval_hit_v0) / count,
            "failure_counts": failure_counts,
        }
