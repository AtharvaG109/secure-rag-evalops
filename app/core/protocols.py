from __future__ import annotations

from typing import Protocol


class RedisClient(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ex: int) -> object: ...
