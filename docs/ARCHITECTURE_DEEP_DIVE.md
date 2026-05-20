# Architecture Deep Dive

## Ingestion design

Parsers normalize supported files into pages. Structure-aware chunking prefers paragraph boundaries for prose and function/class boundaries for code before embeddings are upserted into Qdrant with namespace payloads. The same chunks are indexed into a deterministic graph-memory layer that stores entities, mentions, and document-backed relationships in Postgres.

## Storage policy

Raw files are not retained after ingestion. Postgres stores document metadata, chunk metadata, graph-memory entities/mentions/relations, permissions, eval rows, guardrail events, and cost events.

## Retrieval design

Authorization runs before retrieval. Redis caches query embeddings, Qdrant applies a namespace filter, lexical search scores exact terms from stored chunks, and graph-memory expansion adds chunks connected through stored entities and relations before the blended result set is reranked with MMR.

## Graph memory design

The graph layer is intentionally relational rather than a second database service. Deterministic extraction records title-cased concepts, code-like identifiers, and simple relation verbs such as `uses`, `depends on`, and `connects to`. Graph retrieval is evidence-backed: it only boosts chunks tied to stored mentions or relation evidence, which keeps the feature offline, explainable, and removable with document deletion.

## MMR design

The pure-Python reranker balances relevance and diversity. If vectors are unavailable, it falls back to score order instead of failing.

## Citation validation design

Generated factual answers must cite valid one-based context markers. Missing, zero, negative, out-of-range, or ambiguous citations fail closed.

## Eval metrics and limitations

v0.1 uses deterministic overlap-style metrics for repeatability. They are useful for regressions but are not semantic metrics.

## Guardrail coverage and gaps

The service blocks direct injections, selected unsafe query classes, and indirect injection text in retrieved chunks. Regex-based approaches remain limited and should be supplemented in production.

## Observability design

Trace IDs, JSON logs, latency spans, persisted guardrail rows, and persisted cost rows support debugging and operational review.

## Authentication and audit design

Production requests authenticate with bearer API keys whose keyed hashes are persisted in Postgres. The server derives identity from the key instead of trusting caller-supplied user IDs. Destructive operations emit audit rows so document and collection cleanup actions remain reviewable.

## Threat model

Primary concerns are namespace data leakage, prompt injection, accidental sensitive output, and cost opacity. Controls focus on fail-closed behavior and auditable decisions.

## Future production hardening

Future work includes richer document support, asynchronous ingestion, stronger PII tooling, semantic evaluation, external SSO/OIDC integration, and broader tracing export.
