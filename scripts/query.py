from __future__ import annotations

import httpx
import typer

app = typer.Typer()


@app.command()
def query(
    question: str,
    namespace: str = typer.Option(...),
    user_id: str = typer.Option(...),
    base_url: str = typer.Option("http://localhost:8000"),
) -> None:
    response = httpx.post(
        f"{base_url}/api/v1/query",
        json={"query": question, "namespace": namespace, "user_id": user_id},
        timeout=30.0,
    )
    if response.status_code >= 400:
        typer.echo(response.text)
        raise typer.Exit(code=1)
    payload = response.json()
    typer.echo(payload["answer"])
    for citation in payload["citations"]:
        typer.echo(f"[{citation['index']}] {citation['snippet']} (score: {citation['score']:.3f})")
    citation_status = payload.get("citation_error") or "passed"
    typer.echo(f"citation_validation={citation_status}")
    typer.echo(f"trace_id={payload['trace_id']} latency_ms={payload['latency_ms']:.2f}")


if __name__ == "__main__":
    app()
