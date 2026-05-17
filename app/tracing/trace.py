from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

import structlog

from app.tracing.logger import get_logger

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
logger = get_logger(__name__)


def create_trace_id() -> str:
    trace_id = str(uuid4())
    _trace_id.set(trace_id)
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    return trace_id


def get_trace_id() -> str:
    return _trace_id.get()


@asynccontextmanager
async def trace_span(name: str) -> AsyncIterator[None]:
    started = perf_counter()
    logger.info("span_start", span=name, trace_id=get_trace_id())
    try:
        yield
    except Exception:
        logger.exception(
            "span_error",
            span=name,
            trace_id=get_trace_id(),
            latency_ms=(perf_counter() - started) * 1000,
        )
        raise
    logger.info(
        "span_end",
        span=name,
        trace_id=get_trace_id(),
        latency_ms=(perf_counter() - started) * 1000,
    )
