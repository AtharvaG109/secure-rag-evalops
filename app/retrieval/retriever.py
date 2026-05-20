from __future__ import annotations

import json
import re
from collections import Counter
from hashlib import sha256
from math import sqrt
from time import perf_counter
from typing import Any, cast

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import ChunkORM, DocumentORM
from app.core.protocols import RedisClient
from app.core.schemas import Citation, QueryRequest
from app.core.settings import settings
from app.ingestion.embeddings import EmbeddingClient
from app.memory.graph import GraphMemory, merge_graph_chunks
from app.tracing.trace import trace_span


class ScoredChunk(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int | None = None
    text: str
    score: float
    namespace: str
    source_filename: str
    page_start: int | None
    page_end: int | None
    vector: list[float] | None = None


class RetrievalResult(BaseModel):
    context: str
    citations: list[Citation]
    chunks: list[ScoredChunk]
    chunks_used: int
    retrieval_latency_ms: float


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    denominator = sqrt(sum(value * value for value in left)) * sqrt(
        sum(value * value for value in right)
    )
    if denominator == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*")


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(text)]


class RAGRetriever:
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        qdrant_client: AsyncQdrantClient,
        redis_client: RedisClient,
        session: AsyncSession | None = None,
    ) -> None:
        self._embedding_client = embedding_client
        self._qdrant_client = qdrant_client
        self._redis_client = redis_client
        self._session = session

    async def embed_query(self, query: str) -> list[float]:
        async with trace_span("retrieval.embed_query"):
            return await self._embed_query(query)

    async def _embed_query(self, query: str) -> list[float]:
        cache_key = "emb:" + sha256(query.encode("utf-8")).hexdigest()[:32]
        cached = await self._redis_client.get(cache_key)
        if cached is not None:
            return cast(list[float], json.loads(cached))
        embedding = (await self._embedding_client.embed_batch([query]))[0]
        await self._redis_client.set(cache_key, json.dumps(embedding), ex=300)
        return embedding

    async def vector_search(
        self,
        embedding: list[float],
        namespace: str,
        top_k: int,
    ) -> list[ScoredChunk]:
        async with trace_span("retrieval.vector_search"):
            return await self._vector_search(embedding, namespace, top_k)

    async def _vector_search(
        self,
        embedding: list[float],
        namespace: str,
        top_k: int,
    ) -> list[ScoredChunk]:
        response = await self._qdrant_client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=embedding,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="namespace",
                        match=models.MatchValue(value=namespace),
                    )
                ]
            ),
            limit=top_k,
            with_payload=True,
            with_vectors=True,
        )
        points = response.points
        chunks: list[ScoredChunk] = []
        for point in points:
            payload = cast(dict[str, Any], point.payload or {})
            vector = point.vector if isinstance(point.vector, list) else None
            chunks.append(
                ScoredChunk(
                    chunk_id=str(point.id),
                    document_id=str(payload.get("document_id", "")),
                    chunk_index=cast(int | None, payload.get("chunk_index")),
                    text=str(payload.get("text", "")),
                    score=float(point.score),
                    namespace=str(payload.get("namespace", "")),
                    source_filename=str(payload.get("source_filename", "")),
                    page_start=cast(int | None, payload.get("page_start")),
                    page_end=cast(int | None, payload.get("page_end")),
                    vector=cast(list[float] | None, vector),
                )
            )
        return chunks


    async def lexical_search(self, query: str, namespace: str, top_k: int) -> list[ScoredChunk]:
        if self._session is None:
            return []
        rows = list(
            await self._session.execute(
                select(ChunkORM, DocumentORM)
                .join(DocumentORM, ChunkORM.document_id == DocumentORM.id)
                .where(DocumentORM.namespace == namespace)
            )
        )
        if not rows:
            return []
        query_terms = _tokens(query)
        document_terms = [_tokens(chunk.text) for chunk, _ in rows]
        avg_length = sum(len(terms) for terms in document_terms) / len(document_terms)
        document_frequency = Counter(term for terms in document_terms for term in set(terms))
        scored: list[ScoredChunk] = []
        for (chunk, document), terms in zip(rows, document_terms, strict=True):
            counts = Counter(terms)
            score = 0.0
            for term in query_terms:
                frequency = counts[term]
                if frequency == 0:
                    continue
                inverse_document_frequency = 1.0 + (
                    (len(rows) - document_frequency[term] + 0.5)
                    / (document_frequency[term] + 0.5)
                )
                denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * len(terms) / avg_length)
                score += inverse_document_frequency * (frequency * 2.5 / denominator)
            if score > 0:
                scored.append(
                    ScoredChunk(
                        chunk_id=chunk.id,
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        score=score,
                        namespace=document.namespace,
                        source_filename=document.source_filename,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                    )
                )
        return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:top_k]

    def hybrid_rank(
        self,
        vector_chunks: list[ScoredChunk],
        lexical_chunks: list[ScoredChunk],
        top_k: int,
    ) -> list[ScoredChunk]:
        combined: dict[tuple[str, int | None], ScoredChunk] = {}
        scores: dict[tuple[str, int | None], float] = {}
        max_vector = max((chunk.score for chunk in vector_chunks), default=0.0)
        max_lexical = max((chunk.score for chunk in lexical_chunks), default=0.0)
        for chunk in vector_chunks:
            key = (chunk.document_id, chunk.chunk_index)
            combined[key] = chunk
            vector_score = chunk.score / max_vector if max_vector else 0.0
            scores[key] = scores.get(key, 0.0) + vector_score * 0.4
        for chunk in lexical_chunks:
            key = (chunk.document_id, chunk.chunk_index)
            existing = combined.get(key)
            if existing is None or existing.vector is None:
                combined[key] = chunk
            lexical_score = chunk.score / max_lexical if max_lexical else 0.0
            scores[key] = scores.get(key, 0.0) + lexical_score * 0.6
        ranked = sorted(combined, key=lambda key: scores[key], reverse=True)[:top_k]
        return [combined[key].model_copy(update={"score": scores[key]}) for key in ranked]

    def rerank_mmr(
        self,
        chunks: list[ScoredChunk],
        query_embedding: list[float],
        lambda_: float,
        k: int,
    ) -> list[ScoredChunk]:
        if not chunks:
            return []
        if any(chunk.vector is None for chunk in chunks):
            return sorted(chunks, key=lambda chunk: chunk.score, reverse=True)[:k]

        selected: list[ScoredChunk] = []
        remaining = chunks.copy()
        while remaining and len(selected) < k:
            best_chunk: ScoredChunk | None = None
            best_score = float("-inf")
            for chunk in remaining:
                if chunk.vector is None:
                    continue
                relevance = _cosine_similarity(query_embedding, chunk.vector)
                diversity = max(
                    (
                        _cosine_similarity(chunk.vector, selected_chunk.vector)
                        for selected_chunk in selected
                        if selected_chunk.vector is not None
                    ),
                    default=0.0,
                )
                score = lambda_ * relevance - (1 - lambda_) * diversity
                if score > best_score:
                    best_score = score
                    best_chunk = chunk
            if best_chunk is None:
                break
            selected.append(best_chunk)
            remaining.remove(best_chunk)
        return selected

    def build_context(self, chunks: list[ScoredChunk]) -> tuple[str, list[Citation]]:
        lines: list[str] = []
        citations: list[Citation] = []
        for index, chunk in enumerate(chunks, start=1):
            lines.append(f"[{index}] {chunk.text}")
            citations.append(
                Citation(
                    index=index,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_filename=chunk.source_filename,
                    snippet=chunk.text,
                    score=chunk.score,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                )
            )
        return "\n\n".join(lines), citations

    async def retrieve(self, request: QueryRequest) -> RetrievalResult:
        async with trace_span("retrieval.retrieve"):
            return await self._retrieve(request)

    async def _retrieve(self, request: QueryRequest) -> RetrievalResult:
        started = perf_counter()
        embedding = await self.embed_query(request.query)
        top_k = request.top_k or settings.TOP_K
        vector_chunks = await self.vector_search(embedding, request.namespace, top_k)
        lexical_chunks = await self.lexical_search(request.query, request.namespace, top_k)
        chunks = self.hybrid_rank(vector_chunks, lexical_chunks, top_k)
        if self._session is not None:
            graph_chunks = await GraphMemory(self._session).graph_search(
                request.query,
                request.namespace,
                top_k,
            )
            chunks = merge_graph_chunks(chunks, graph_chunks, top_k)
        reranked = self.rerank_mmr(chunks, embedding, settings.MMR_LAMBDA, settings.MMR_K)
        context, citations = self.build_context(reranked)
        return RetrievalResult(
            context=context,
            citations=citations,
            chunks=reranked,
            chunks_used=len(reranked),
            retrieval_latency_ms=(perf_counter() - started) * 1000,
        )
