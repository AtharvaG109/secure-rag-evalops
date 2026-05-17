from __future__ import annotations

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, get_current_user
from app.core.authz import NamespaceAuthz
from app.core.dependencies import (
    get_cost_tracker,
    get_guardrail_service,
    get_namespace_authz,
    get_response_generator,
    get_retriever,
)
from app.core.schemas import QueryRequest, QueryResponse
from app.guardrails.service import GuardrailService
from app.retrieval.citations import CitationValidationError, validate_citations
from app.retrieval.generator import ResponseGenerator
from app.retrieval.retriever import RAGRetriever
from app.tracing.cost_tracker import CostTracker
from app.tracing.trace import create_trace_id

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    retriever: Annotated[RAGRetriever, Depends(get_retriever)],
    generator: Annotated[ResponseGenerator, Depends(get_response_generator)],
    guardrails: Annotated[GuardrailService, Depends(get_guardrail_service)],
    cost_tracker: Annotated[CostTracker, Depends(get_cost_tracker)],
) -> QueryResponse:
    started = perf_counter()
    trace_id = create_trace_id()
    try:
        await authz.require_read(current_user.user_id, request.namespace)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "access_denied", "reason": str(exc)},
        ) from exc
    pre_query_result = await guardrails.pre_query_check(
        request.query,
        current_user.user_id,
        request.namespace,
        trace_id,
    )
    if pre_query_result is not None:
        raise HTTPException(
            status_code=400,
            detail={"error": "guardrail_blocked", "reason": pre_query_result.reason},
        )
    retrieval = await retriever.retrieve(
        request.model_copy(update={"user_id": current_user.user_id})
    )
    chunk_result = await guardrails.check_retrieved_chunks(
        retrieval.chunks,
        current_user.user_id,
        request.namespace,
        trace_id,
    )
    if chunk_result is not None:
        raise HTTPException(
            status_code=400,
            detail={"error": "guardrail_blocked", "reason": chunk_result.reason},
        )
    generation = await generator.generate(request.query, retrieval.context)
    citation_error: str | None = None
    try:
        validate_citations(generation.answer, retrieval.citations)
    except CitationValidationError as exc:
        citation_error = str(exc)
    await cost_tracker.record(
        trace_id=trace_id,
        model="chat",
        prompt_tokens=generation.prompt_tokens,
        completion_tokens=generation.completion_tokens,
    )
    # Embedding token counts are unavailable from this path, so no synthetic event is recorded.
    answer = await guardrails.redact_answer(
        generation.answer,
        current_user.user_id,
        request.namespace,
        trace_id,
    )
    return QueryResponse(
        answer=answer,
        citations=retrieval.citations,
        trace_id=trace_id,
        latency_ms=(perf_counter() - started) * 1000,
        citation_error=citation_error,
    )
