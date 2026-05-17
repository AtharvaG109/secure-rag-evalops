from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from app.core.settings import settings
from app.ingestion.chunker import ChunkCandidate


class VectorStore:
    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client

    async def ensure_collection(self) -> None:
        exists = await self._client.collection_exists(settings.QDRANT_COLLECTION)
        if exists:
            return
        await self._client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )

    async def delete_document(self, document_id: str) -> None:
        await self._client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    async def upsert_chunks(
        self,
        chunks: list[ChunkCandidate],
        embeddings: list[list[float]],
        document_id: str,
        namespace: str,
        source_filename: str,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        points: list[models.PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            points.append(
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk.chunk_index}")),
                    vector=embedding,
                    payload={
                        "text": chunk.text,
                        "document_id": document_id,
                        "namespace": namespace,
                        "chunk_index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                        "source_filename": source_filename,
                        "page_start": chunk.page_start,
                        "page_end": chunk.page_end,
                    },
                )
            )
        for start in range(0, len(points), 100):
            await self._client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=points[start : start + 100],
            )
        return len(points)
