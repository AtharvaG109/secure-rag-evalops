from __future__ import annotations

import subprocess
from asyncio import wait_for
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routers.audit import router as audit_router
from app.api.routers.auth import router as auth_router
from app.api.routers.documents import router as documents_router
from app.api.routers.eval import router as eval_router
from app.api.routers.ingest import router as ingest_router
from app.api.routers.metrics import router as metrics_router
from app.api.routers.query import router as query_router
from app.core.database import engine
from app.core.security import RedisRateLimitMiddleware, RequestSizeLimitMiddleware, trusted_hosts
from app.core.settings import settings
from app.tracing.logger import configure_logging
from app.ui import router as web_router

APP_VERSION = "0.1.0"


def run_migrations() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.validate_for_runtime()
    configure_logging(settings.LOG_LEVEL)
    if settings.RUN_MIGRATIONS_ON_STARTUP and settings.ENVIRONMENT == "local":
        run_migrations()
    yield


app = FastAPI(title="SecureRAG EvalOps", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RedisRateLimitMiddleware)
if trusted_hosts() != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts())
app.include_router(web_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(ingest_router)
app.include_router(documents_router)
app.include_router(eval_router)
app.include_router(query_router)
app.include_router(metrics_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION, "environment": settings.ENVIRONMENT}


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready() -> JSONResponse:
    dependencies: dict[str, str] = {}
    try:
        async with engine.connect() as connection:
            await wait_for(connection.execute(text("SELECT 1")), timeout=2.0)
        dependencies["postgres"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["postgres"] = "error"
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await wait_for(redis.ping(), timeout=2.0)
        dependencies["redis"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["redis"] = "error"
    finally:
        await redis.aclose()  # type: ignore[attr-defined]  # redis stubs lag runtime API
    qdrant = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    try:
        await wait_for(qdrant.get_collections(), timeout=2.0)
        dependencies["qdrant"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["qdrant"] = "error"
    finally:
        await qdrant.close()
    status_code = 200 if all(value == "ok" for value in dependencies.values()) else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if status_code == 200 else "degraded",
            "dependencies": dependencies,
        },
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(_: Request, exc: PermissionError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": "access_denied", "reason": str(exc)},
    )
