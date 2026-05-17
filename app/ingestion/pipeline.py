from __future__ import annotations

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import ChunkORM, CollectionORM, DocumentORM
from app.core.schemas import IngestRequest, IngestResponse
from app.core.settings import settings
from app.ingestion.chunker import chunk_pages
from app.ingestion.embeddings import EmbeddingClient
from app.ingestion.parsers import parse_file
from app.ingestion.vector_store import VectorStore
from app.tracing.trace import trace_span


class IngestionPipeline:
    def __init__(
        self,
        session: AsyncSession,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
    ) -> None:
        self._session = session
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    async def run(self, request: IngestRequest) -> IngestResponse:
        async with trace_span("ingestion.run"):
            return await self._run(request)

    async def _run(self, request: IngestRequest) -> IngestResponse:
        content_bytes = request.content.encode("utf-8")
        file_hash = sha256(content_bytes).hexdigest()
        collection = await self._session.scalar(
            select(CollectionORM).where(
                CollectionORM.namespace == request.namespace,
                CollectionORM.name == request.collection_name,
            )
        )
        if collection is None:
            collection = CollectionORM(namespace=request.namespace, name=request.collection_name)
            self._session.add(collection)
            await self._session.flush()

        existing = await self._session.scalar(
            select(DocumentORM).where(
                DocumentORM.file_hash == file_hash,
                DocumentORM.namespace == request.namespace,
            )
        )
        if existing is not None:
            return IngestResponse(
                document_id=existing.id,
                chunk_count=0,
                status="duplicate_skipped",
            )

        pages = parse_file(request.content, request.source_type, request.source_filename)
        chunks = chunk_pages(
            pages,
            settings.CHUNK_SIZE,
            settings.CHUNK_OVERLAP,
            source_type=request.source_type,
        )
        embeddings = await self._embedding_client.embed_batch([chunk.text for chunk in chunks])
        await self._vector_store.ensure_collection()

        document = DocumentORM(
            namespace=request.namespace,
            collection_id=collection.id,
            source_type=request.source_type,
            source_filename=request.source_filename,
            file_hash=file_hash,
            metadata_json=request.metadata,
        )
        self._session.add(document)
        await self._session.flush()
        await self._vector_store.upsert_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id=document.id,
            namespace=request.namespace,
            source_filename=request.source_filename,
        )
        self._session.add_all(
            [
                ChunkORM(
                    document_id=document.id,
                    text=chunk.text,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                )
                for chunk in chunks
            ]
        )
        await self._session.commit()
        return IngestResponse(
            document_id=document.id,
            chunk_count=len(chunks),
            status="completed",
        )
