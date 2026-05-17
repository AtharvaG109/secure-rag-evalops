from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import GuardrailEventORM
from app.core.schemas import GuardrailResult
from app.guardrails.injection_detector import detect_injection
from app.guardrails.pii_redactor import redact_pii
from app.guardrails.unsafe_filter import filter_unsafe_query
from app.retrieval.retriever import ScoredChunk
from app.tracing.trace import trace_span


class GuardrailService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _persist(
        self,
        check_name: str,
        reason: str,
        user_id: str,
        namespace: str,
        trace_id: str,
        blocked: bool,
    ) -> None:
        self._session.add(
            GuardrailEventORM(
                trace_id=trace_id,
                user_id=user_id,
                namespace=namespace,
                check_name=check_name,
                reason=reason,
                blocked=blocked,
            )
        )
        await self._session.commit()

    async def pre_query_check(
        self,
        query: str,
        user_id: str,
        namespace: str,
        trace_id: str,
    ) -> GuardrailResult | None:
        async with trace_span("guardrails.pre_query_check"):
            return await self._pre_query_check(query, user_id, namespace, trace_id)

    async def _pre_query_check(
        self,
        query: str,
        user_id: str,
        namespace: str,
        trace_id: str,
    ) -> GuardrailResult | None:
        unsafe = filter_unsafe_query(query)
        if not unsafe.passed:
            await self._persist(
                "unsafe_query",
                unsafe.reason or "unsafe_query",
                user_id,
                namespace,
                trace_id,
                True,
            )
            return unsafe
        injection = detect_injection(query)
        if not injection.passed:
            await self._persist(
                "prompt_injection",
                injection.reason or "prompt_injection_detected",
                user_id,
                namespace,
                trace_id,
                True,
            )
            return injection
        return None

    async def check_retrieved_chunks(
        self,
        chunks: list[ScoredChunk],
        user_id: str,
        namespace: str,
        trace_id: str,
    ) -> GuardrailResult | None:
        async with trace_span("guardrails.check_retrieved_chunks"):
            return await self._check_retrieved_chunks(chunks, user_id, namespace, trace_id)

    async def _check_retrieved_chunks(
        self,
        chunks: list[ScoredChunk],
        user_id: str,
        namespace: str,
        trace_id: str,
    ) -> GuardrailResult | None:
        for chunk in chunks:
            if not detect_injection(chunk.text).passed:
                result = GuardrailResult(passed=False, reason="indirect_injection_in_context")
                await self._persist(
                    "indirect_prompt_injection",
                    result.reason or "indirect_injection_in_context",
                    user_id,
                    namespace,
                    trace_id,
                    True,
                )
                return result
        return None

    async def redact_answer(
        self,
        answer: str,
        user_id: str,
        namespace: str,
        trace_id: str,
    ) -> str:
        async with trace_span("guardrails.redact_answer"):
            return await self._redact_answer(answer, user_id, namespace, trace_id)

    async def _redact_answer(
        self,
        answer: str,
        user_id: str,
        namespace: str,
        trace_id: str,
    ) -> str:
        redacted = redact_pii(answer)
        if redacted.count > 0:
            await self._persist(
                "pii_redaction",
                "pii_redacted",
                user_id,
                namespace,
                trace_id,
                False,
            )
        return redacted.text
