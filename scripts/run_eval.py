from __future__ import annotations

import time
from pathlib import Path

import httpx
import typer
from rich.table import Table

app = typer.Typer()


@app.command()
def run_eval(
    dataset_path: Path,
    namespace: str = typer.Option(...),
    user_id: str = typer.Option(...),
    base_url: str = typer.Option("http://localhost:8000"),
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
    table = Table(title="Evaluation thresholds")
    table.add_column("Metric")
    table.add_column("Threshold")
    for metric, threshold in [
        ("citation_validity_v0", "0.95"),
        ("keyword_overlap_v0", "0.50"),
        ("context_recall_v0", "0.75"),
        ("retrieval_hit_rate", "0.75"),
        ("p95_latency_ms", "2000"),
    ]:
        table.add_row(metric, threshold)
    typer.echo(table)


if __name__ == "__main__":
    app()
