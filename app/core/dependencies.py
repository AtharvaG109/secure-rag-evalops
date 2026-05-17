from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import NamespaceAuthz
from app.core.database import get_session
from app.core.protocols import RedisClient
from app.core.settings import settings
from app.evaluation.runner import EvalRunner
from app.guardrails.service import GuardrailService
from app.ingestion.embeddings import EmbeddingClient
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.vector_store import VectorStore
from app.retrieval.generator import ResponseGenerator
from app.retrieval.retriever import RAGRetriever
from app.tracing.cost_tracker import CostTracker


def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def get_redis_client() -> RedisClient:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


def get_vector_store(
    qdrant_client: Annotated[AsyncQdrantClient, Depends(get_qdrant_client)],
) -> VectorStore:
    return VectorStore(qdrant_client)


def get_ingestion_pipeline(
    session: Annotated[AsyncSession, Depends(get_session)],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> IngestionPipeline:
    return IngestionPipeline(session, embedding_client, vector_store)


def get_namespace_authz(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NamespaceAuthz:
    return NamespaceAuthz(session)


def get_retriever(
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    qdrant_client: Annotated[AsyncQdrantClient, Depends(get_qdrant_client)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RAGRetriever:
    return RAGRetriever(embedding_client, qdrant_client, redis_client, session)


def get_response_generator() -> ResponseGenerator:
    return ResponseGenerator()


def get_eval_runner(
    session: Annotated[AsyncSession, Depends(get_session)],
    retriever: Annotated[RAGRetriever, Depends(get_retriever)],
    generator: Annotated[ResponseGenerator, Depends(get_response_generator)],
) -> EvalRunner:
    return EvalRunner(session, retriever, generator)


def get_guardrail_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GuardrailService:
    return GuardrailService(session)


def get_cost_tracker(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CostTracker:
    return CostTracker(session)
