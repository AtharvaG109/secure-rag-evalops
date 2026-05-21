from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.authz import NamespaceAuthz
from app.core.database import get_session
from app.core.dependencies import get_namespace_authz
from app.core.orm import ChunkORM, DocumentORM, EntityMentionORM, EntityORM, EntityRelationORM
from app.core.schemas import GraphEdge, GraphNode, GraphResponse

router = APIRouter(prefix="/api/v1", tags=["graph"])


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    namespace: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
    search: str | None = None,
    entity_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 80,
) -> GraphResponse:
    try:
        await authz.require_read(current_user.user_id, namespace)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "access_denied", "reason": str(exc)},
        ) from exc

    node_query = (
        select(EntityORM, func.count(EntityMentionORM.id))
        .outerjoin(EntityMentionORM, EntityMentionORM.entity_id == EntityORM.id)
        .where(EntityORM.namespace == namespace)
        .group_by(EntityORM.id)
        .order_by(func.count(EntityMentionORM.id).desc(), EntityORM.display_name.asc())
        .limit(limit)
    )

    relation_query = (
        select(EntityRelationORM, ChunkORM, DocumentORM)
        .join(ChunkORM, ChunkORM.id == EntityRelationORM.evidence_chunk_id)
        .join(DocumentORM, DocumentORM.id == ChunkORM.document_id)
        .where(EntityRelationORM.namespace == namespace)
        .order_by(EntityRelationORM.created_at.desc())
    )
    if entity_id:
        seed_ids = {entity_id}
        relation_rows = list(
            await session.execute(
                relation_query.where(
                    (EntityRelationORM.source_entity_id == entity_id)
                    | (EntityRelationORM.target_entity_id == entity_id)
                ).limit(limit)
            )
        )
        related_ids = {
            connected_id
            for relation, _, _ in relation_rows
            for connected_id in (relation.source_entity_id, relation.target_entity_id)
        } | seed_ids
        node_rows = list(
            await session.execute(
                select(EntityORM, func.count(EntityMentionORM.id))
                .outerjoin(EntityMentionORM, EntityMentionORM.entity_id == EntityORM.id)
                .where(EntityORM.id.in_(related_ids), EntityORM.namespace == namespace)
                .group_by(EntityORM.id)
                .order_by(func.count(EntityMentionORM.id).desc(), EntityORM.display_name.asc())
            )
        )
    elif search:
        node_rows = list(
            await session.execute(
                node_query.where(
                    EntityORM.display_name.ilike(_contains_pattern(search), escape="\\")
                )
            )
        )
        seed_ids = {entity.id for entity, _ in node_rows}
        if not seed_ids:
            return GraphResponse(nodes=[], edges=[])
        relation_query = relation_query.where(
            (EntityRelationORM.source_entity_id.in_(seed_ids))
            | (EntityRelationORM.target_entity_id.in_(seed_ids))
        ).limit(limit * 2)
        relation_rows = list(await session.execute(relation_query))
        related_ids = {
            entity_id
            for relation, _, _ in relation_rows
            for entity_id in (relation.source_entity_id, relation.target_entity_id)
        } | seed_ids
        node_rows = list(
            await session.execute(
                select(EntityORM, func.count(EntityMentionORM.id))
                .outerjoin(EntityMentionORM, EntityMentionORM.entity_id == EntityORM.id)
                .where(EntityORM.id.in_(related_ids), EntityORM.namespace == namespace)
                .group_by(EntityORM.id)
                .order_by(func.count(EntityMentionORM.id).desc(), EntityORM.display_name.asc())
            )
        )
    else:
        relation_rows = list(await session.execute(relation_query.limit(limit * 2)))
        seed_ids = {
            entity_id
            for relation, _, _ in relation_rows
            for entity_id in (relation.source_entity_id, relation.target_entity_id)
        }
        if not seed_ids:
            node_rows = list(await session.execute(node_query))
            return GraphResponse(
                nodes=[
                    GraphNode(
                        id=entity.id,
                        label=entity.display_name,
                        entity_type=entity.entity_type,
                        mention_count=mention_count,
                    )
                    for entity, mention_count in node_rows
                ],
                edges=[],
            )
        node_rows = list(
            await session.execute(
                select(EntityORM, func.count(EntityMentionORM.id))
                .outerjoin(EntityMentionORM, EntityMentionORM.entity_id == EntityORM.id)
                .where(EntityORM.id.in_(seed_ids), EntityORM.namespace == namespace)
                .group_by(EntityORM.id)
                .order_by(func.count(EntityMentionORM.id).desc(), EntityORM.display_name.asc())
            )
        )
    return GraphResponse(
        nodes=[
            GraphNode(
                id=entity.id,
                label=entity.display_name,
                entity_type=entity.entity_type,
                mention_count=mention_count,
            )
            for entity, mention_count in node_rows
        ],
        edges=[
            GraphEdge(
                id=relation.id,
                source=relation.source_entity_id,
                target=relation.target_entity_id,
                relation_type=relation.relation_type,
                evidence_chunk_id=relation.evidence_chunk_id,
                source_filename=document.source_filename,
                snippet=chunk.text[:240],
                confidence=relation.confidence,
            )
            for relation, chunk, document in relation_rows
        ],
    )
