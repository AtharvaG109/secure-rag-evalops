from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.settings import settings

RequestHandler = Callable[[Request], Awaitable[Response]]


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > settings.MAX_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={"error": "request_too_large"},
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        if settings.RATE_LIMIT_PER_MINUTE <= 0:
            return await call_next(request)
        client_ip = request.client.host if request.client is not None else "unknown"
        key = f"ratelimit:{client_ip}"
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
        finally:
            await redis.aclose()  # type: ignore[attr-defined]  # redis stubs lag runtime API
        if count > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(status_code=429, content={"error": "rate_limited"})
        return await call_next(request)


def trusted_hosts() -> list[str]:
    return [host.strip() for host in settings.TRUSTED_HOSTS.split(",") if host.strip()]


def error_payload(error: str, **extra: Any) -> dict[str, Any]:
    return {"error": error, **extra}
