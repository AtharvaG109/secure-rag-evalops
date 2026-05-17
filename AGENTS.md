# Codex Agent Instructions — SecureRAG EvalOps

SecureRAG EvalOps is a private-deployment Python RAG evaluation and guardrail platform.

## Core rules

- Keep the app buildable after every change.
- Prefer working implementations over broad skeletons.
- Do not add placeholder tests, `assert True`, or TODOs in critical paths.
- Keep namespace authorization before retrieval and keep Qdrant namespace filters in place.
- Preserve fail-closed citation validation.
- Do not persist raw source files after ingestion.
- Do not auto-run Alembic outside explicit local opt-in behavior.
- Do not reintroduce external AI-provider requirements into the default local path.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy async + Postgres
- Alembic
- Redis
- Qdrant
- Pydantic v2
- pytest, Ruff, mypy strict

## Validation

After changes, run:

```bash
poetry run ruff check .
poetry run mypy app --strict
poetry run pytest -q
```
