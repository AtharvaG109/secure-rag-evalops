from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import NamespaceAccessORM
from app.core.settings import settings

_PERMISSION_ORDER = {"read": 1, "write": 2, "admin": 3}


class NamespaceAuthz:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def check_access(
        self,
        user_id: str,
        namespace: str,
        required_permission: str,
    ) -> bool:
        if (
            settings.ENVIRONMENT == "local"
            and settings.ALLOW_LOCAL_DEV_AUTH
            and user_id == settings.LOCAL_DEV_USER_ID
        ):
            return True
        access = await self._session.scalar(
            select(NamespaceAccessORM).where(
                NamespaceAccessORM.user_id == user_id,
                NamespaceAccessORM.namespace == namespace,
            )
        )
        if access is None:
            return False
        return _PERMISSION_ORDER[access.permission] >= _PERMISSION_ORDER[required_permission]

    async def require_read(self, user_id: str, namespace: str) -> None:
        if not await self.check_access(user_id, namespace, "read"):
            raise PermissionError("namespace_not_permitted")

    async def require_write(self, user_id: str, namespace: str) -> None:
        if not await self.check_access(user_id, namespace, "write"):
            raise PermissionError("namespace_not_permitted")

    async def require_admin(self, user_id: str, namespace: str) -> None:
        if not await self.check_access(user_id, namespace, "admin"):
            raise PermissionError("namespace_not_permitted")
