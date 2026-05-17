from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.core.database import get_session
from app.core.orm import CostEventORM
from app.main import app


class FakeSession:
    async def scalars(self, _: object) -> list[Any]:
        return [
            CostEventORM(
                trace_id="t",
                model="chat",
                prompt_tokens=1,
                completion_tokens=1,
                embedding_tokens=0,
                chat_cost_usd=0.1,
                embedding_cost_usd=0.0,
                total_cost_usd=0.1,
                created_at=datetime.now(UTC),
            )
        ]


def test_cost_metrics_aggregate_rows() -> None:
    app.dependency_overrides[get_session] = lambda: FakeSession()
    with TestClient(app) as client:
        response = client.get("/api/v1/metrics/cost")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["estimated_total_usd"] == 0.1
