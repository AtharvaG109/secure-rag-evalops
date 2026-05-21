from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.dependencies import get_eval_runner
from app.core.orm import CostEventORM, EvalResultORM, EvalRunORM, GuardrailEventORM
from app.main import app


class FakeRun:
    id = "run-1"


class FakeRunner:
    async def run_batch(self, **_: object) -> FakeRun:
        return FakeRun()


class FakeReportSession:
    def __init__(self) -> None:
        self.calls = 0
        self.run = EvalRunORM(
            id="run-1",
            pipeline_version="v0.1",
            namespace="security-policy",
            status="completed",
            started_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
            completed_at=datetime(2026, 5, 20, 10, 1, tzinfo=UTC),
        )
        self.results = [
            EvalResultORM(
                run_id="run-1",
                query="Is MFA required?",
                expected_answer="MFA is required.",
                generated_answer="MFA is required [1].",
                citation_validity_v0=1.0,
                keyword_overlap_v0=1.0,
                context_recall_v0=1.0,
                retrieval_hit_v0=True,
                failure_type="passed",
                latency_ms=25.0,
            ),
            EvalResultORM(
                run_id="run-1",
                query="What is the vendor policy?",
                expected_answer="Vendors need SOC 2.",
                generated_answer="Vendors need SOC 2.",
                citation_validity_v0=0.0,
                keyword_overlap_v0=1.0,
                context_recall_v0=1.0,
                retrieval_hit_v0=True,
                failure_type="invalid_citation",
                latency_ms=50.0,
            ),
        ]
        self.guardrails = [
            GuardrailEventORM(
                trace_id="trace-1",
                user_id="demo-admin",
                namespace="security-policy",
                check_name="prompt_injection_detected",
                reason="direct_prompt_injection",
                blocked=True,
            )
        ]
        self.costs = [
            CostEventORM(
                trace_id="trace-1",
                model="local",
                prompt_tokens=10,
                completion_tokens=5,
                embedding_tokens=12,
                chat_cost_usd=0.0,
                embedding_cost_usd=0.0,
                total_cost_usd=0.0,
            )
        ]

    async def get(self, _: object, __: str) -> EvalRunORM:
        return self.run

    async def scalars(self, _: object) -> list[object]:
        self.calls += 1
        if self.calls == 1:
            return self.results
        if self.calls == 2:
            return self.guardrails
        return self.costs


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


def test_eval_api_returns_rich_report() -> None:
    from app.core.database import get_session

    app.dependency_overrides[get_session] = lambda: FakeReportSession()
    with TestClient(app) as client:
        response = client.get("/api/v1/eval/run-1/report")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["sample_count"] == 2
    assert body["summary"]["retrieval_hit_rate"] == 1.0
    assert body["failed_citation_examples"][0]["query"] == "What is the vendor policy?"
    assert body["guardrail_outcomes"][0]["blocked_count"] == 1


def test_eval_api_returns_markdown_report() -> None:
    from app.core.database import get_session

    app.dependency_overrides[get_session] = lambda: FakeReportSession()
    with TestClient(app) as client:
        response = client.get("/api/v1/eval/run-1/report?format=md")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "# Evaluation Report: run-1" in response.text
    assert "Failed Citation Examples" in response.text
