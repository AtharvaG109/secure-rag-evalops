from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "securerag_chunks"
    REDIS_URL: str = "redis://localhost:6379/0"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/securerag"
    EMBEDDING_PROVIDER: str = "local_hash"
    GENERATION_PROVIDER: str = "extractive"
    EMBEDDING_DIMENSIONS: int = 3072
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "embeddinggemma"
    OLLAMA_CHAT_MODEL: str = "gemma3"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K: int = 8
    MMR_LAMBDA: float = 0.5
    MMR_K: int = 6
    CHAT_INPUT_PRICE_PER_1M: float = 0.0
    CHAT_OUTPUT_PRICE_PER_1M: float = 0.0
    EMBEDDING_PRICE_PER_1M: float = 0.0
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: Literal["local", "test", "production"] = "local"
    RUN_MIGRATIONS_ON_STARTUP: bool = False
    ALLOW_LOCAL_DEV_AUTH: bool = True
    LOCAL_DEV_USER_ID: str = "demo-admin"
    AUTH_TOKEN_PEPPER: str = "dev-only-change-me"
    MAX_REQUEST_BYTES: int = 10_000_000
    MAX_INGEST_CONTENT_CHARS: int = 10_000_000
    RATE_LIMIT_PER_MINUTE: int = 0
    TRUSTED_HOSTS: str = "*"

    def validate_for_runtime(self) -> None:
        if self.ENVIRONMENT != "production":
            return
        insecure: list[str] = []
        if self.ALLOW_LOCAL_DEV_AUTH:
            insecure.append("ALLOW_LOCAL_DEV_AUTH")
        if self.AUTH_TOKEN_PEPPER == "dev-only-change-me":
            insecure.append("AUTH_TOKEN_PEPPER")
        if self.RATE_LIMIT_PER_MINUTE <= 0:
            insecure.append("RATE_LIMIT_PER_MINUTE")
        if self.TRUSTED_HOSTS == "*":
            insecure.append("TRUSTED_HOSTS")
        if insecure:
            names = ", ".join(insecure)
            raise RuntimeError(f"insecure_production_settings: {names}")


settings = Settings()
