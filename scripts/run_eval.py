from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


def _format_score(value: float) -> str:
    return f"{value:.3f}"


@app.command()
def run_eval(
    dataset_path: Path,
    namespace: str = typer.Option(...),
    user_id: str = typer.Option(...),
    base_url: str = typer.Option("http://localhost:8000"),
    report_out: Annotated[
        Path | None,
        typer.Option(help="Write the Markdown eval report."),
    ] = None,
) -> None:
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        run_id = client.post(
            "/api/v1/eval/run",
            json={
                "dataset_path": str(dataset_path),
                "pipeline_version": "v0.1",
                "namespace": namespace,
                "user_id": user_id,
            },
        ).json()["run_id"]
        while True:
            run = client.get(f"/api/v1/eval/{run_id}").json()
            if run["status"] == "completed":
                break
            time.sleep(0.5)
        report = client.get(f"/api/v1/eval/{run_id}/report").json()
        if report_out is not None:
            markdown = client.get(
                f"/api/v1/eval/{run_id}/report",
                params={"format": "md"},
            ).text
            report_out.write_text(markdown, encoding="utf-8")

    summary = report["summary"]
    latency = report["latency"]
    table = Table(title=f"Evaluation report: {run_id}")
    table.add_column("Metric")
    table.add_column("Actual")
    table.add_column("Threshold")
    for metric, actual, threshold in [
        ("citation_validity_v0", _format_score(summary["citation_validity_v0"]), "0.95"),
        ("keyword_overlap_v0", _format_score(summary["keyword_overlap_v0"]), "0.50"),
        ("context_recall_v0", _format_score(summary["context_recall_v0"]), "0.75"),
        ("retrieval_hit_rate", _format_score(summary["retrieval_hit_rate"]), "0.75"),
        ("p95_latency_ms", f"{latency['p95_ms']:.1f}", "2000"),
    ]:
        table.add_row(metric, actual, threshold)
    console.print(table)
    if report["failed_citation_examples"]:
        typer.echo("Failed citation examples:")
        for example in report["failed_citation_examples"]:
            typer.echo(f"- {example['query']}: {example['failure_type']}")
    if report_out is not None:
        typer.echo(f"wrote {report_out}")


if __name__ == "__main__":
    app()
