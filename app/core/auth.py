from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import new as hmac_new
from secrets import token_urlsafe
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.orm import ApiKeyORM, UserORM
from app.core.settings import settings


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    is_superuser: bool
    auth_method: str


def hash_api_key(token: str) -> str:
    return hmac_new(
        settings.AUTH_TOKEN_PEPPER.encode("utf-8"),
        token.encode("utf-8"),
        sha256,
    ).hexdigest()


def generate_api_key() -> str:
    return f"srg_live_{token_urlsafe(32)}"


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUser:
    authorization = request.headers.get("authorization")
    if authorization is None:
        if settings.ENVIRONMENT == "local" and settings.ALLOW_LOCAL_DEV_AUTH:
            return CurrentUser(
                user_id=settings.LOCAL_DEV_USER_ID,
                is_superuser=True,
                auth_method="local_dev",
            )
        raise HTTPException(status_code=401, detail={"error": "authentication_required"})
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail={"error": "invalid_authorization_header"})
    api_key = await session.scalar(
        select(ApiKeyORM).where(
            ApiKeyORM.key_hash == hash_api_key(token),
            ApiKeyORM.revoked_at.is_(None),
        )
    )
    if api_key is None:
        raise HTTPException(status_code=401, detail={"error": "invalid_api_key"})
    user = await session.get(UserORM, api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail={"error": "inactive_user"})
    api_key.last_used_at = datetime.now(UTC)
    await session.commit()
    return CurrentUser(
        user_id=user.id,
        is_superuser=user.is_superuser,
        auth_method="api_key",
    )


def require_superuser(current_user: CurrentUser) -> None:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail={"error": "admin_required"})
