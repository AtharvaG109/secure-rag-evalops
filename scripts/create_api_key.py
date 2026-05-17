from __future__ import annotations

import asyncio

import typer
from sqlalchemy import select

from app.core.auth import generate_api_key, hash_api_key
from app.core.database import async_session_factory
from app.core.orm import ApiKeyORM, NamespaceAccessORM, UserORM

app = typer.Typer(add_completion=False)


@app.command()
def create(
    user_id: str,
    email: str,
    display_name: str,
    namespace: str,
    permission: str = "admin",
    superuser: bool = False,
) -> None:
    asyncio.run(
        _create(
            user_id=user_id,
            email=email,
            display_name=display_name,
            namespace=namespace,
            permission=permission,
            superuser=superuser,
        )
    )


async def _create(
    *,
    user_id: str,
    email: str,
    display_name: str,
    namespace: str,
    permission: str,
    superuser: bool,
) -> None:
    if permission not in {"read", "write", "admin"}:
        raise typer.BadParameter("permission must be read, write, or admin")
    token = generate_api_key()
    async with async_session_factory() as session:
        user = await session.get(UserORM, user_id)
        if user is None:
            user = UserORM(
                id=user_id,
                email=email,
                display_name=display_name,
                is_superuser=superuser,
            )
            session.add(user)
        else:
            user.email = email
            user.display_name = display_name
            user.is_superuser = superuser
        access = await session.scalar(
            select(NamespaceAccessORM).where(
                NamespaceAccessORM.user_id == user_id,
                NamespaceAccessORM.namespace == namespace,
            )
        )
        if access is None:
            session.add(
                NamespaceAccessORM(
                    user_id=user_id,
                    namespace=namespace,
                    permission=permission,
                )
            )
        else:
            access.permission = permission
        session.add(
            ApiKeyORM(
                user_id=user_id,
                key_prefix=token[:16],
                key_hash=hash_api_key(token),
            )
        )
        await session.commit()
    typer.echo(token)


if __name__ == "__main__":
    app()
