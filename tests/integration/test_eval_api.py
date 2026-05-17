from fastapi.testclient import TestClient

from app.core.dependencies import get_eval_runner
from app.main import app


class FakeRun:
    id = "run-1"


class FakeRunner:
    async def run_batch(self, **_: object) -> FakeRun:
        return FakeRun()


def test_eval_api_returns_run_id() -> None:
    app.dependency_overrides[get_eval_runner] = lambda: FakeRunner()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/eval/run",
            json={
                "dataset_path": "evals/golden_set.jsonl",
                "pipeline_version": "v0.1",
                "namespace": "security-policy",
                "user_id": "demo-admin",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"run_id": "run-1"}
