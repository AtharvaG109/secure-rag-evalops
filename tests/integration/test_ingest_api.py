from fastapi.testclient import TestClient

from app.core.dependencies import get_ingestion_pipeline, get_namespace_authz
from app.core.schemas import IngestResponse
from app.main import app


class AllowAuthz:
    async def require_write(self, _: str, __: str) -> None:
        return None


class DenyAuthz:
    async def require_write(self, _: str, __: str) -> None:
        raise PermissionError("namespace_not_permitted")


class FakePipeline:
    async def run(self, _: object) -> IngestResponse:
        return IngestResponse(document_id="doc-1", chunk_count=1, status="completed")


def test_ingest_api_returns_pipeline_response() -> None:
    app.dependency_overrides[get_namespace_authz] = lambda: AllowAuthz()
    app.dependency_overrides[get_ingestion_pipeline] = lambda: FakePipeline()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingest",
            json={
                "source_type": "txt",
                "content": "SOC 2 reports are required.",
                "namespace": "security-policy",
                "user_id": "demo-admin",
                "source_filename": "policy.txt",
                "metadata": {},
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_ingest_requires_write_permission() -> None:
    app.dependency_overrides[get_namespace_authz] = lambda: DenyAuthz()
    app.dependency_overrides[get_ingestion_pipeline] = lambda: FakePipeline()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingest",
            json={
                "source_type": "txt",
                "content": "SOC 2 reports are required.",
                "namespace": "security-policy",
                "user_id": "analyst",
                "source_filename": "policy.txt",
                "metadata": {},
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 403
