from typing import Any

import pytest

from app.core.orm import DocumentORM
from app.core.schemas import IngestRequest
from app.ingestion.pipeline import IngestionPipeline


class FakeScalarResult:
    def __init__(self, value: DocumentORM | None) -> None:
        self.value = value


class FakeSession:
    def __init__(self, existing: DocumentORM | None = None) -> None:
        self.existing = existing
        self.added: list[Any] = []
        self.committed = False

    async def scalar(self, _: object) -> DocumentORM | None:
        return self.existing

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        document = self.added[0]
        if isinstance(document, DocumentORM):
            document.id = "doc-1"

    def add_all(self, items: list[Any]) -> None:
        self.added.extend(items)

    async def commit(self) -> None:
        self.committed = True


class FakeEmbeddingClient:
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts = 0

    async def ensure_collection(self) -> None:
        return None

    async def upsert_chunks(self, **_: Any) -> int:
        self.upserts += 1
        return 1


@pytest.mark.asyncio
async def test_duplicate_ingest_returns_duplicate_skipped() -> None:
    existing = DocumentORM(
        id="doc-existing",
        namespace="security-policy",
        source_type="txt",
        source_filename="policy.txt",
        file_hash="hash",
        metadata_json={},
    )
    pipeline = IngestionPipeline(
        FakeSession(existing),  # type: ignore[arg-type]
        FakeEmbeddingClient(),  # type: ignore[arg-type]
        FakeVectorStore(),  # type: ignore[arg-type]
    )

    response = await pipeline.run(
        IngestRequest(
            source_type="txt",
            content="hello",
            namespace="security-policy",
            user_id="demo-admin",
            source_filename="policy.txt",
        )
    )

    assert response.status == "duplicate_skipped"
    assert response.document_id == "doc-existing"
