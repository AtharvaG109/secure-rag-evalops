from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, require_superuser
from app.core.database import get_session
from app.core.orm import AuditEventORM

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/events")
async def list_audit_events(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 100,
) -> list[dict[str, object]]:
    require_superuser(current_user)
    rows = list(
        await session.scalars(
            select(AuditEventORM).order_by(desc(AuditEventORM.created_at)).limit(limit)
        )
    )
    return [
        {
            "actor_user_id": row.actor_user_id,
            "namespace": row.namespace,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "details": row.details_json,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
