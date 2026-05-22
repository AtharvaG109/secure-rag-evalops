# Release Checklist

Use this checklist before publishing SecureRAG EvalOps changes.

## Local Gates

```bash
poetry run ruff check .
poetry run mypy app --strict
poetry run pytest -q
```

When integration behavior changes, also run the service dependencies and migration path:

```bash
make docker-up
make migrate
make check
make docker-down
```

## Security Review

- Namespace authorization runs before retrieval.
- Qdrant queries include namespace filters.
- Citation validation fails closed.
- Guardrail events are recorded without logging raw secrets.
- Raw source files are not persisted after ingestion.
- External AI-provider requirements are not reintroduced into the default local path.

## Release Readiness

- CI passes.
- README and docs match changed behavior.
- Demo corpus, eval fixtures, and screenshots contain synthetic data only.
