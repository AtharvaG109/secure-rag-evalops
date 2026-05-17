from __future__ import annotations

import base64
from pathlib import Path

import httpx
import typer
from rich.progress import track

app = typer.Typer()


def _read_content(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return base64.b64encode(path.read_bytes()).decode("ascii")
    return path.read_text(encoding="utf-8")


@app.command()
def ingest_dir(
    directory: Path,
    namespace: str = typer.Option(...),
    user_id: str = typer.Option(...),
    base_url: str = typer.Option("http://localhost:8000"),
    extensions: str = typer.Option(".txt .md .pdf .json .py .c .cpp .cc .cxx .java .h .hpp"),
) -> None:
    allowed = set(extensions.split())
    counts = {"completed": 0, "duplicate_skipped": 0, "failed": 0}
    if directory.is_file():
        files = [directory] if directory.suffix in allowed else []
    else:
        files = [path for path in directory.rglob("*") if path.is_file() and path.suffix in allowed]
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        for path in track(files, description="Ingesting files"):
            try:
                response = client.post(
                    "/api/v1/ingest",
                    json={
                        "source_type": path.suffix.lstrip("."),
                        "content": _read_content(path),
                        "namespace": namespace,
                        "user_id": user_id,
                        "source_filename": path.name,
                        "metadata": {},
                    },
                )
                response.raise_for_status()
                status = response.json()["status"]
                counts[status] += 1
                typer.echo(f"{path}: {status}")
            except Exception:
                counts["failed"] += 1
                typer.echo(f"{path}: failed")
    typer.echo(str(counts))


if __name__ == "__main__":
    app()
