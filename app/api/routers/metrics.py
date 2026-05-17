from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, require_superuser
from app.core.database import get_session
from app.core.orm import CostEventORM, EvalResultORM, EvalRunORM, GuardrailEventORM

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def _period_start() -> datetime:
    return datetime.now(UTC) - timedelta(hours=24)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    index = min(round((len(values) - 1) * percentile), len(values) - 1)
    return sorted(values)[index]


@router.get("/cost")
async def cost_metrics(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, float | int | str]:
    require_superuser(current_user)
    rows = list(
        await session.scalars(
            select(CostEventORM).where(CostEventORM.created_at >= _period_start())
        )
    )
    return {
        "estimated_total_usd": sum(row.total_cost_usd for row in rows),
        "chat_usd": sum(row.chat_cost_usd for row in rows),
        "embedding_usd": sum(row.embedding_cost_usd for row in rows),
        "event_count": len(rows),
        "period": "24h",
    }


@router.get("/guardrails")
async def guardrail_metrics(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, int]:
    require_superuser(current_user)
    rows = list(
        await session.scalars(
            select(GuardrailEventORM).where(GuardrailEventORM.created_at >= _period_start())
        )
    )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.check_name] = counts.get(row.check_name, 0) + 1
    return counts


@router.get("/latency")
async def latency_metrics(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, float | int]:
    require_superuser(current_user)
    rows = list(await session.scalars(select(EvalResultORM.latency_ms)))
    return {
        "p50": _percentile(rows, 0.50),
        "p95": _percentile(rows, 0.95),
        "p99": _percentile(rows, 0.99),
        "mean": mean(rows) if rows else 0.0,
        "sample_count": len(rows),
    }


@router.get("/eval")
async def eval_metrics(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    require_superuser(current_user)
    run = await session.scalar(
        select(EvalRunORM)
        .where(EvalRunORM.completed_at.is_not(None))
        .order_by(desc(EvalRunORM.completed_at))
    )
    if run is None:
        return {"run_id": None, "status": "no_completed_runs"}
    return {"run_id": run.id, "status": run.status, "namespace": run.namespace}
