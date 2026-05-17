from typing import Any

import pytest

from app.ingestion.chunker import ChunkCandidate
from app.ingestion.vector_store import VectorStore


class FakeQdrant:
    def __init__(self) -> None:
        self.points: list[Any] = []
        self.deleted: Any = None

    async def collection_exists(self, _: str) -> bool:
        return True

    async def upsert(self, *, collection_name: str, points: list[Any]) -> None:
        _ = collection_name
        self.points.extend(points)

    async def delete(self, *, collection_name: str, points_selector: Any) -> None:
        _ = collection_name
        self.deleted = points_selector


@pytest.mark.asyncio
async def test_qdrant_payload_includes_namespace() -> None:
    qdrant = FakeQdrant()
    store = VectorStore(qdrant)  # type: ignore[arg-type]
    chunk = ChunkCandidate(text="hello", chunk_index=0, token_count=1, page_start=1, page_end=1)

    count = await store.upsert_chunks([chunk], [[0.1]], "doc-1", "security-policy", "policy.txt")

    assert count == 1
    assert qdrant.points[0].payload["namespace"] == "security-policy"
    assert qdrant.points[0].id == "96bfba1f-a026-5f29-9cb6-eef33495c01d"


@pytest.mark.asyncio
async def test_delete_document_filters_by_document_id() -> None:
    qdrant = FakeQdrant()
    store = VectorStore(qdrant)  # type: ignore[arg-type]

    await store.delete_document("doc-1")

    assert qdrant.deleted.filter.must[0].match.value == "doc-1"
