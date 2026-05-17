from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
async def whoami(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str | bool]:
    return {
        "user_id": current_user.user_id,
        "is_superuser": current_user.is_superuser,
        "auth_method": current_user.auth_method,
    }
