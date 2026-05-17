from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.authz import NamespaceAuthz
from app.core.database import get_session
from app.core.dependencies import get_eval_runner, get_namespace_authz
from app.core.orm import EvalResultORM, EvalRunORM
from app.evaluation.runner import EvalRunner

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])


class EvalRunRequest(BaseModel):
    dataset_path: str
    pipeline_version: str
    namespace: str
    user_id: str


@router.post("/run")
async def run_eval(
    request: EvalRunRequest,
    background_tasks: BackgroundTasks,
    runner: Annotated[EvalRunner, Depends(get_eval_runner)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
) -> dict[str, str]:
    await authz.require_write(current_user.user_id, request.namespace)
    run = await runner.run_batch(
        dataset_path=request.dataset_path,
        pipeline_version=request.pipeline_version,
        namespace=request.namespace,
        user_id=current_user.user_id,
    )
    background_tasks.add_task(lambda: None)
    return {"run_id": run.id}


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    run = await session.get(EvalRunORM, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    await authz.require_read(current_user.user_id, run.namespace)
    return {
        "run_id": run.id,
        "status": run.status,
        "pipeline_version": run.pipeline_version,
        "namespace": run.namespace,
    }


@router.get("/{run_id}/results")
async def get_results(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, Any]]:
    run = await session.get(EvalRunORM, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    await authz.require_read(current_user.user_id, run.namespace)
    results = await session.scalars(select(EvalResultORM).where(EvalResultORM.run_id == run_id))
    return [
        {
            "query": result.query,
            "failure_type": result.failure_type,
            "citation_validity_v0": result.citation_validity_v0,
        }
        for result in results
    ]


@router.get("/{run_id}/failures")
async def get_failures(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, Any]]:
    run = await session.get(EvalRunORM, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    await authz.require_read(current_user.user_id, run.namespace)
    results = await session.scalars(
        select(EvalResultORM).where(
            EvalResultORM.run_id == run_id,
            EvalResultORM.failure_type != "passed",
        )
    )
    return [{"query": result.query, "failure_type": result.failure_type} for result in results]
