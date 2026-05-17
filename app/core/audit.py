from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import AuditEventORM


async def record_audit_event(
    session: AsyncSession,
    *,
    actor_user_id: str,
    action: str,
    target_type: str,
    namespace: str | None = None,
    target_id: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEventORM(
            actor_user_id=actor_user_id,
            namespace=namespace,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=details or {},
        )
    )
