from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import CostEventORM, EvalResultORM, EvalRunORM, GuardrailEventORM
from app.core.schemas import (
    EvalCostSummary,
    EvalFailedCitationExample,
    EvalGuardrailOutcome,
    EvalLatencySummary,
    EvalMetricSummary,
    EvalQuestionReport,
    EvalReportResponse,
)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    index = min(round((len(values) - 1) * percentile), len(values) - 1)
    return sorted(values)[index]


def _build_metric_summary(results: list[EvalResultORM]) -> EvalMetricSummary:
    if not results:
        return EvalMetricSummary(
            sample_count=0,
            citation_validity_v0=0.0,
            keyword_overlap_v0=0.0,
            context_recall_v0=0.0,
            retrieval_hit_rate=0.0,
            failure_counts={},
        )
    failure_counts: dict[str, int] = {}
    for result in results:
        failure_counts[result.failure_type] = failure_counts.get(result.failure_type, 0) + 1
    count = len(results)
    return EvalMetricSummary(
        sample_count=count,
        citation_validity_v0=sum(result.citation_validity_v0 for result in results) / count,
        keyword_overlap_v0=sum(result.keyword_overlap_v0 for result in results) / count,
        context_recall_v0=sum(result.context_recall_v0 for result in results) / count,
        retrieval_hit_rate=sum(1 for result in results if result.retrieval_hit_v0) / count,
        failure_counts=failure_counts,
    )


def _build_latency_summary(results: list[EvalResultORM]) -> EvalLatencySummary:
    latencies = [result.latency_ms for result in results]
    return EvalLatencySummary(
        sample_count=len(latencies),
        mean_ms=mean(latencies) if latencies else 0.0,
        p50_ms=_percentile(latencies, 0.50),
        p95_ms=_percentile(latencies, 0.95),
        max_ms=max(latencies) if latencies else 0.0,
    )


def _build_guardrail_outcomes(rows: list[GuardrailEventORM]) -> list[EvalGuardrailOutcome]:
    grouped: dict[str, tuple[int, int]] = {}
    for row in rows:
        count, blocked_count = grouped.get(row.check_name, (0, 0))
        grouped[row.check_name] = (count + 1, blocked_count + int(row.blocked))
    return [
        EvalGuardrailOutcome(
            check_name=check_name,
            count=count,
            blocked_count=blocked_count,
        )
        for check_name, (count, blocked_count) in sorted(grouped.items())
    ]


def _build_cost_summary(rows: list[CostEventORM]) -> EvalCostSummary:
    return EvalCostSummary(
        estimated_total_usd=sum(row.total_cost_usd for row in rows),
        chat_usd=sum(row.chat_cost_usd for row in rows),
        embedding_usd=sum(row.embedding_cost_usd for row in rows),
        event_count=len(rows),
    )


async def build_eval_report(
    session: AsyncSession,
    run_id: str,
) -> EvalReportResponse | None:
    run = await session.get(EvalRunORM, run_id)
    if run is None:
        return None
    results = list(
        await session.scalars(
            select(EvalResultORM)
            .where(EvalResultORM.run_id == run_id)
            .order_by(EvalResultORM.created_at.asc(), EvalResultORM.query.asc())
        )
    )
    window_end = run.completed_at or datetime.now(UTC)
    guardrail_rows = list(
        await session.scalars(
            select(GuardrailEventORM).where(
                GuardrailEventORM.namespace == run.namespace,
                GuardrailEventORM.created_at >= run.started_at,
                GuardrailEventORM.created_at <= window_end,
            )
        )
    )
    cost_rows = list(
        await session.scalars(
            select(CostEventORM).where(
                CostEventORM.created_at >= run.started_at,
                CostEventORM.created_at <= window_end,
            )
        )
    )
    return EvalReportResponse(
        run_id=run.id,
        status=run.status,
        namespace=run.namespace,
        pipeline_version=run.pipeline_version,
        summary=_build_metric_summary(results),
        latency=_build_latency_summary(results),
        cost=_build_cost_summary(cost_rows),
        guardrail_outcomes=_build_guardrail_outcomes(guardrail_rows),
        questions=[
            EvalQuestionReport(
                query=result.query,
                failure_type=result.failure_type,
                retrieval_hit_v0=result.retrieval_hit_v0,
                citation_validity_v0=result.citation_validity_v0,
                keyword_overlap_v0=result.keyword_overlap_v0,
                context_recall_v0=result.context_recall_v0,
                latency_ms=result.latency_ms,
                generated_answer=result.generated_answer,
            )
            for result in results
        ],
        failed_citation_examples=[
            EvalFailedCitationExample(
                query=result.query,
                generated_answer=result.generated_answer,
                failure_type=result.failure_type,
                citation_validity_v0=result.citation_validity_v0,
            )
            for result in results
            if result.citation_validity_v0 < 1.0 or result.failure_type == "invalid_citation"
        ][:5],
    )


def render_eval_report_markdown(report: EvalReportResponse) -> str:
    summary = report.summary
    latency = report.latency
    cost = report.cost
    lines = [
        f"# Evaluation Report: {report.run_id}",
        "",
        f"- Status: {report.status}",
        f"- Namespace: {report.namespace}",
        f"- Pipeline version: {report.pipeline_version}",
        f"- Samples: {summary.sample_count}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Citation validity | {summary.citation_validity_v0:.3f} |",
        f"| Keyword overlap | {summary.keyword_overlap_v0:.3f} |",
        f"| Context recall | {summary.context_recall_v0:.3f} |",
        f"| Retrieval hit rate | {summary.retrieval_hit_rate:.3f} |",
        "",
        "## Latency And Cost",
        "",
        f"- Mean latency: {latency.mean_ms:.1f} ms",
        f"- p95 latency: {latency.p95_ms:.1f} ms",
        f"- Max latency: {latency.max_ms:.1f} ms",
        f"- Estimated cost: ${cost.estimated_total_usd:.4f} across {cost.event_count} events",
        "",
        "## Guardrail Outcomes",
        "",
    ]
    if report.guardrail_outcomes:
        lines.extend(
            [
                "| Check | Count | Blocked |",
                "| --- | ---: | ---: |",
                *[
                    f"| {outcome.check_name} | {outcome.count} | {outcome.blocked_count} |"
                    for outcome in report.guardrail_outcomes
                ],
            ]
        )
    else:
        lines.append("No guardrail events were recorded during the run window.")
    lines.extend(["", "## Per-Question Results", "", "| Query | Hit | Citation | Failure |"])
    lines.append("| --- | ---: | ---: | --- |")
    lines.extend(
        f"| {question.query} | {str(question.retrieval_hit_v0).lower()} | "
        f"{question.citation_validity_v0:.3f} | {question.failure_type} |"
        for question in report.questions
    )
    lines.extend(["", "## Failed Citation Examples", ""])
    if report.failed_citation_examples:
        for example in report.failed_citation_examples:
            lines.extend(
                [
                    f"### {example.query}",
                    "",
                    f"- Failure: {example.failure_type}",
                    f"- Citation validity: {example.citation_validity_v0:.3f}",
                    f"- Generated answer: {example.generated_answer}",
                    "",
                ]
            )
    else:
        lines.append("No failed citation examples were recorded.")
    return "\n".join(lines).strip() + "\n"
