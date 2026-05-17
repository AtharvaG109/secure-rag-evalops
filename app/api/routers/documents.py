from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.auth import CurrentUser, get_current_user
from app.core.authz import NamespaceAuthz
from app.core.database import get_session
from app.core.dependencies import get_namespace_authz, get_vector_store
from app.core.orm import ChunkORM, CollectionORM, DocumentORM
from app.core.schemas import (
    CleanupDocumentsRequest,
    CleanupResponse,
    CollectionRecord,
    DeleteDocumentResponse,
    DocumentRecord,
    UpsertCollectionRequest,
)
from app.ingestion.vector_store import VectorStore

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents", response_model=list[DocumentRecord])
async def list_documents(
    namespace: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 100,
    offset: int = 0,
) -> list[DocumentRecord]:
    try:
        await authz.require_read(current_user.user_id, namespace)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "access_denied", "reason": str(exc)},
        ) from exc
    rows = list(
        await session.execute(
            select(DocumentORM, CollectionORM, func.count(ChunkORM.id))
            .outerjoin(CollectionORM, CollectionORM.id == DocumentORM.collection_id)
            .outerjoin(ChunkORM, ChunkORM.document_id == DocumentORM.id)
            .where(DocumentORM.namespace == namespace)
            .group_by(DocumentORM.id, CollectionORM.id)
            .order_by(DocumentORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return [
        DocumentRecord(
            id=document.id,
            namespace=document.namespace,
            collection_name=collection.name if collection is not None else None,
            source_type=document.source_type,
            source_filename=document.source_filename,
            chunk_count=chunk_count,
            created_at=document.created_at.isoformat(),
        )
        for document, collection, chunk_count in rows
    ]


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> DeleteDocumentResponse:
    document = await session.scalar(select(DocumentORM).where(DocumentORM.id == document_id))
    if document is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    try:
        await authz.require_write(current_user.user_id, document.namespace)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "access_denied", "reason": str(exc)},
        ) from exc
    await vector_store.delete_document(document_id)
    await record_audit_event(
        session,
        actor_user_id=current_user.user_id,
        namespace=document.namespace,
        action="document.delete",
        target_type="document",
        target_id=document.id,
        details={"source_filename": document.source_filename},
    )
    await session.delete(document)
    await session.commit()
    return DeleteDocumentResponse(document_id=document_id, deleted=True)


@router.get("/collections", response_model=list[CollectionRecord])
async def list_collections(
    namespace: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CollectionRecord]:
    await authz.require_read(current_user.user_id, namespace)
    collections = list(
        await session.scalars(
            select(CollectionORM)
            .where(CollectionORM.namespace == namespace)
            .order_by(CollectionORM.name)
        )
    )
    return [
        CollectionRecord(
            id=collection.id,
            namespace=collection.namespace,
            name=collection.name,
            retention_days=collection.retention_days,
        )
        for collection in collections
    ]


@router.post("/collections", response_model=CollectionRecord)
async def upsert_collection(
    request: UpsertCollectionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CollectionRecord:
    await authz.require_write(current_user.user_id, request.namespace)
    collection = await session.scalar(
        select(CollectionORM).where(
            CollectionORM.namespace == request.namespace,
            CollectionORM.name == request.name,
        )
    )
    if collection is None:
        collection = CollectionORM(namespace=request.namespace, name=request.name)
        session.add(collection)
    collection.retention_days = request.retention_days
    await record_audit_event(
        session,
        actor_user_id=current_user.user_id,
        namespace=request.namespace,
        action="collection.upsert",
        target_type="collection",
        target_id=collection.id,
        details={"name": request.name, "retention_days": request.retention_days},
    )
    await session.commit()
    return CollectionRecord(
        id=collection.id,
        namespace=collection.namespace,
        name=collection.name,
        retention_days=collection.retention_days,
    )


@router.post("/collections/cleanup", response_model=CleanupResponse)
async def cleanup_expired_documents(
    namespace: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> CleanupResponse:
    await authz.require_write(current_user.user_id, namespace)
    rows = list(
        await session.execute(
            select(DocumentORM, CollectionORM)
            .join(CollectionORM, CollectionORM.id == DocumentORM.collection_id)
            .where(
                DocumentORM.namespace == namespace,
                CollectionORM.retention_days.is_not(None),
            )
        )
    )
    deleted = 0
    now = datetime.now(UTC)
    for document, collection in rows:
        if collection.retention_days is None:
            continue
        if document.created_at <= now - timedelta(days=collection.retention_days):
            await vector_store.delete_document(document.id)
            await session.delete(document)
            deleted += 1
    await record_audit_event(
        session,
        actor_user_id=current_user.user_id,
        namespace=namespace,
        action="collection.cleanup_expired",
        target_type="namespace",
        target_id=namespace,
        details={"deleted_documents": deleted},
    )
    await session.commit()
    return CleanupResponse(deleted_documents=deleted)


@router.post("/documents/cleanup", response_model=CleanupResponse)
async def cleanup_documents(
    request: CleanupDocumentsRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> CleanupResponse:
    if request.collection_name is None and request.older_than_days is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_cleanup_filter",
                "reason": "collection_name_or_older_than_days_required",
            },
        )
    await authz.require_write(current_user.user_id, request.namespace)
    query = (
        select(DocumentORM)
        .outerjoin(CollectionORM, CollectionORM.id == DocumentORM.collection_id)
        .where(DocumentORM.namespace == request.namespace)
    )
    if request.collection_name is not None:
        query = query.where(CollectionORM.name == request.collection_name)
    if request.older_than_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=request.older_than_days)
        query = query.where(DocumentORM.created_at <= cutoff)
    documents = list(await session.scalars(query))
    if request.dry_run or not request.confirm:
        return CleanupResponse(
            deleted_documents=0,
            matched_documents=len(documents),
            dry_run=True,
        )
    for document in documents:
        await vector_store.delete_document(document.id)
        await session.delete(document)
    await record_audit_event(
        session,
        actor_user_id=current_user.user_id,
        namespace=request.namespace,
        action="document.bulk_delete",
        target_type="namespace",
        target_id=request.namespace,
        details={
            "collection_name": request.collection_name,
            "older_than_days": request.older_than_days,
            "deleted_documents": len(documents),
        },
    )
    await session.commit()
    return CleanupResponse(
        deleted_documents=len(documents),
        matched_documents=len(documents),
        dry_run=False,
    )
