# Demo Proof Notes

Generated from a local demo run on 2026-05-20 using `bash scripts/demo.sh`.

## Cited Answer

```text
== cited answer with validation status ==
Critical vendors require SOC 2 Type II evidence before onboarding and during each annual vendor review. [1]
...
citation_validation=passed
```

## Namespace Filtering

```text
== namespace-filtered empty result ==
I don't have enough information in the provided context to answer this question.
citation_validation=passed
```

The same question answered in `security-policy` returned cited context, while `empty-policy` returned no answer. This demonstrates that namespace filtering happens before answer generation.

## Graph Memory

```text
== graph memory preview ==
{"nodes":[{"label":"Restricted","entity_type":"concept","mention_count":10},{"label":"Vendor","entity_type":"concept","mention_count":10},{"label":"SOC 2 Type II","entity_type":"concept","mention_count":5}],"edges":[{"relation_type":"requires","source_filename":"acceptable_use.md","confidence":1.0}]}
```

The graph endpoint returns extracted entities, relations, evidence chunk IDs, source filenames, snippets, and confidence values.

## Evaluation Report

```text
Evaluation report: 9611158d-f96b-4bd3-9129-6cee887391da

Metric                 Actual  Threshold
citation_validity_v0   1.000   0.95
keyword_overlap_v0     0.748   0.50
context_recall_v0      0.915   0.75
retrieval_hit_rate     1.000   0.75
p95_latency_ms         145.7   2000
wrote /tmp/securerag-eval-report.md
```

The Markdown report also included per-question retrieval hit status, citation validity, failure categories, latency, and estimated cost.

## Guardrail Rejection

```text
== guardrail rejection ==
{"detail":{"error":"guardrail_blocked","reason":"prompt_injection_detected"}}
```

The prompt-injection probe was rejected before retrieval and answer generation.
