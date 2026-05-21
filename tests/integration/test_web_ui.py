from fastapi.testclient import TestClient

from app.main import app


def test_web_ui_homepage() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "SecureRAG EvalOps" in response.text
    assert 'data-tab="guardrails"' in response.text
    assert 'data-tab="graph"' in response.text
    assert 'id="file"' in response.text
    assert "/api/v1/ingest" in response.text
    assert "/api/v1/query" in response.text
    assert "/api/v1/documents" in response.text
    assert "/api/v1/documents/cleanup" in response.text
    assert "/api/v1/graph" in response.text
    assert "/api/v1/metrics/guardrails" in response.text
