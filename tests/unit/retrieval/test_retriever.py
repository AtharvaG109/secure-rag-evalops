from types import SimpleNamespace
from typing import Any

import pytest

from app.retrieval.retriever import RAGRetriever, ScoredChunk


class FakeEmbeddingClient:
    async def embed_batch(self, _: list[str]) -> list[list[float]]:
        return [[1.0, 0.0]]


class FakeRedis:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.cache.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        _ = ex
        self.cache[key] = value


class FakeQdrant:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    async def query_points(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="chunk-1",
                    score=0.9,
                    vector=[1.0, 0.0],
                    payload={
                        "document_id": "doc-1",
                        "text": "MFA is required.",
                        "namespace": "security-policy",
                        "source_filename": "policy.md",
                        "page_start": 1,
                        "page_end": 1,
                    },
                )
            ]
        )


@pytest.mark.asyncio
async def test_qdrant_search_filters_namespace_and_requests_vectors() -> None:
    qdrant = FakeQdrant()
    retriever = RAGRetriever(
        FakeEmbeddingClient(),  # type: ignore[arg-type]
        qdrant,  # type: ignore[arg-type]
        FakeRedis(),  # type: ignore[arg-type]
    )

    chunks = await retriever.vector_search([1.0, 0.0], "security-policy", 3)

    assert chunks[0].namespace == "security-policy"
    assert qdrant.kwargs["with_vectors"] is True
    assert qdrant.kwargs["query_filter"].must[0].match.value == "security-policy"


def test_mmr_uses_vectors() -> None:
    retriever = RAGRetriever(None, None, None)  # type: ignore[arg-type]
    chunks = [
        ScoredChunk(
            chunk_id="a",
            document_id="d",
            text="a",
            score=0.9,
            namespace="n",
            source_filename="a",
            page_start=1,
            page_end=1,
            vector=[1.0, 0.0],
        ),
        ScoredChunk(
            chunk_id="b",
            document_id="d",
            text="b",
            score=0.8,
            namespace="n",
            source_filename="b",
            page_start=1,
            page_end=1,
            vector=[0.0, 1.0],
        ),
    ]
    assert [chunk.chunk_id for chunk in retriever.rerank_mmr(chunks, [1.0, 0.0], 0.5, 2)] == [
        "a",
        "b",
    ]


def test_mmr_falls_back_to_score_order_without_vectors() -> None:
    retriever = RAGRetriever(None, None, None)  # type: ignore[arg-type]
    chunks = [
        ScoredChunk(
            chunk_id="a",
            document_id="d",
            text="a",
            score=0.1,
            namespace="n",
            source_filename="a",
            page_start=1,
            page_end=1,
        ),
        ScoredChunk(
            chunk_id="b",
            document_id="d",
            text="b",
            score=0.9,
            namespace="n",
            source_filename="b",
            page_start=1,
            page_end=1,
        ),
    ]
    assert [chunk.chunk_id for chunk in retriever.rerank_mmr(chunks, [1.0, 0.0], 0.5, 2)] == [
        "b",
        "a",
    ]


def test_context_uses_one_based_citations() -> None:
    retriever = RAGRetriever(None, None, None)  # type: ignore[arg-type]
    context, citations = retriever.build_context(
        [
            ScoredChunk(
                chunk_id="a",
                document_id="d",
                text="MFA is required.",
                score=0.9,
                namespace="n",
                source_filename="policy.md",
                page_start=1,
                page_end=1,
            )
        ]
    )
    assert context.startswith("[1]")
    assert citations[0].index == 1


class FakeChunk:
    def __init__(self, chunk_id: str, text: str, chunk_index: int) -> None:
        self.id = chunk_id
        self.text = text
        self.chunk_index = chunk_index
        self.page_start = 1
        self.page_end = 1


class FakeDocument:
    def __init__(self, document_id: str) -> None:
        self.id = document_id
        self.namespace = "security-policy"
        self.source_filename = "policy.md"


class FakeScalarRows:
    def __init__(self, rows: list[tuple[FakeChunk, FakeDocument]]) -> None:
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)


class FakeSession:
    async def execute(self, _: object) -> FakeScalarRows:
        document = FakeDocument("doc-1")
        return FakeScalarRows([
            (FakeChunk("c1", "unrelated vendor language", 0), document),
            (FakeChunk("c2", "MFA is required for all systems", 1), document),
        ])


@pytest.mark.asyncio
async def test_lexical_search_prefers_exact_term_matches() -> None:
    retriever = RAGRetriever(None, None, None, FakeSession())  # type: ignore[arg-type]

    chunks = await retriever.lexical_search("MFA systems", "security-policy", 2)

    assert chunks[0].chunk_id == "c2"


def test_hybrid_rank_blends_vector_and_lexical_results() -> None:
    retriever = RAGRetriever(None, None, None)  # type: ignore[arg-type]
    vector = ScoredChunk(
        chunk_id="v",
        document_id="d1",
        chunk_index=0,
        text="vector",
        score=1.0,
        namespace="n",
        source_filename="a",
        page_start=1,
        page_end=1,
        vector=[1.0, 0.0],
    )
    lexical = ScoredChunk(
        chunk_id="l",
        document_id="d2",
        chunk_index=0,
        text="exact phrase",
        score=2.0,
        namespace="n",
        source_filename="b",
        page_start=1,
        page_end=1,
    )

    ranked = retriever.hybrid_rank([vector], [lexical], 2)

    assert ranked[0].chunk_id == "l"
