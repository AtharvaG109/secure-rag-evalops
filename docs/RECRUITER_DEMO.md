# Recruiter Demo

This is the shortest path for showing what SecureRAG EvalOps does without requiring an external AI provider.

## Run

```bash
cp .env.example .env
make docker-up
make install
make migrate
make dev
bash scripts/demo.sh
```

## What To Point Out

1. Ingestion reads the demo corpus, chunks it, stores namespace-scoped vectors in Qdrant, and indexes graph-memory entities and relations in Postgres.
2. The first query prints a concise answer, numbered citations, `citation_validation=passed`, a trace ID, and latency.
3. The empty-namespace query shows retrieval isolation: the same question against a namespace with no documents cannot reuse `security-policy` chunks.
4. `/api/v1/graph` returns extracted entities, relations, evidence chunk IDs, and source filenames.
5. `scripts/run_eval.py --report-out /tmp/securerag-eval-report.md` prints actual evaluation metrics and writes a Markdown report with per-question retrieval hit status, citation validity, failures, guardrail outcomes, latency, and cost.
6. The prompt-injection request is rejected by the guardrail path before retrieval and generation.

## Expected Proof Signals

- `make check` passes Ruff, strict mypy, and the pytest suite.
- Cited answers include source snippets rather than unsupported claims.
- Citation failures are surfaced in reports instead of being hidden.
- Namespace filters are enforced before retrieval and in Qdrant payload filters.
- The default workflow stays offline and deterministic; stronger local models are optional.

See [DEMO_PROOF.md](DEMO_PROOF.md) for a compact transcript from a successful local run.
