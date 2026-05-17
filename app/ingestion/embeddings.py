from __future__ import annotations

import re
from collections.abc import Sequence
from hashlib import sha256
from math import sqrt
from typing import cast

import httpx

from app.core.settings import settings

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


class EmbeddingClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if len(texts) > 100:
            raise ValueError("embedding batch size must not exceed 100")
        if settings.EMBEDDING_PROVIDER == "ollama":
            return await self._embed_with_ollama(texts)
        return [self._embed_text(text) for text in texts]

    async def _embed_with_ollama(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._http_client or httpx.AsyncClient(base_url=settings.OLLAMA_URL)
        should_close = self._http_client is None
        try:
            response = await client.post(
                "/api/embed",
                json={"model": settings.OLLAMA_EMBEDDING_MODEL, "input": list(texts)},
            )
            response.raise_for_status()
            embeddings = cast(list[list[float]], response.json()["embeddings"])
        finally:
            if should_close:
                await client.aclose()
        for embedding in embeddings:
            if len(embedding) != settings.EMBEDDING_DIMENSIONS:
                raise ValueError("embedding dimension mismatch")
        return embeddings

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * settings.EMBEDDING_DIMENSIONS
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % settings.EMBEDDING_DIMENSIONS
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
