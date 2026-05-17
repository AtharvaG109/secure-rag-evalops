from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, get_current_user
from app.core.authz import NamespaceAuthz
from app.core.dependencies import get_ingestion_pipeline, get_namespace_authz
from app.core.schemas import IngestRequest, IngestResponse
from app.core.settings import settings
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    authz: Annotated[NamespaceAuthz, Depends(get_namespace_authz)],
    pipeline: Annotated[IngestionPipeline, Depends(get_ingestion_pipeline)],
) -> IngestResponse:
    if len(request.content) > settings.MAX_INGEST_CONTENT_CHARS:
        raise HTTPException(status_code=413, detail={"error": "ingest_content_too_large"})
    try:
        await authz.require_write(current_user.user_id, request.namespace)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "access_denied", "reason": str(exc)},
        ) from exc
    return await pipeline.run(request.model_copy(update={"user_id": current_user.user_id}))
