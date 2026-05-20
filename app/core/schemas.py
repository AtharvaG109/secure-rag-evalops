from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    index: int
    chunk_id: str
    document_id: str
    source_filename: str
    snippet: str
    score: float
    page_start: int | None = None
    page_end: int | None = None


class IngestRequest(BaseModel):
    source_type: str
    content: str
    namespace: str
    user_id: str | None = None
    source_filename: str
    collection_name: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    document_id: str
    chunk_count: int
    status: Literal["completed", "duplicate_skipped"]


class QueryRequest(BaseModel):
    query: str
    namespace: str
    user_id: str | None = None
    top_k: int | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    trace_id: str
    latency_ms: float
    citation_error: str | None = None


class EvalSample(BaseModel):
    query: str
    expected_answer: str
    ground_truth_contexts: list[str]
    namespace: str


class EvalResult(BaseModel):
    query: str
    expected_answer: str
    generated_answer: str
    citation_validity_v0: float
    keyword_overlap_v0: float
    context_recall_v0: float
    retrieval_hit_v0: bool
    failure_type: str
    latency_ms: float


class EvalMetricSummary(BaseModel):
    sample_count: int
    citation_validity_v0: float
    keyword_overlap_v0: float
    context_recall_v0: float
    retrieval_hit_rate: float
    failure_counts: dict[str, int]


class EvalLatencySummary(BaseModel):
    sample_count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float


class EvalCostSummary(BaseModel):
    estimated_total_usd: float
    chat_usd: float
    embedding_usd: float
    event_count: int


class EvalGuardrailOutcome(BaseModel):
    check_name: str
    count: int
    blocked_count: int


class EvalQuestionReport(BaseModel):
    query: str
    failure_type: str
    retrieval_hit_v0: bool
    citation_validity_v0: float
    keyword_overlap_v0: float
    context_recall_v0: float
    latency_ms: float
    generated_answer: str


class EvalFailedCitationExample(BaseModel):
    query: str
    generated_answer: str
    failure_type: str
    citation_validity_v0: float


class EvalReportResponse(BaseModel):
    run_id: str
    status: str
    namespace: str
    pipeline_version: str
    summary: EvalMetricSummary
    latency: EvalLatencySummary
    cost: EvalCostSummary
    guardrail_outcomes: list[EvalGuardrailOutcome]
    questions: list[EvalQuestionReport]
    failed_citation_examples: list[EvalFailedCitationExample]


class GuardrailResult(BaseModel):
    passed: bool
    reason: str | None = None


class NamespacePermission(BaseModel):
    user_id: str
    namespace: str
    permission: Literal["read", "write", "admin"]


class CostRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trace_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    embedding_tokens: int
    chat_cost_usd: float
    embedding_cost_usd: float
    total_cost_usd: float


class CollectionRecord(BaseModel):
    id: str
    namespace: str
    name: str
    retention_days: int | None


class UpsertCollectionRequest(BaseModel):
    namespace: str
    name: str
    user_id: str | None = None
    retention_days: int | None = None


class CleanupResponse(BaseModel):
    deleted_documents: int
    matched_documents: int = 0
    dry_run: bool = False


class CleanupDocumentsRequest(BaseModel):
    namespace: str
    user_id: str | None = None
    collection_name: str | None = None
    older_than_days: int | None = Field(default=None, ge=0)
    dry_run: bool = True
    confirm: bool = False


class DocumentRecord(BaseModel):
    id: str
    namespace: str
    collection_name: str | None
    source_type: str
    source_filename: str
    chunk_count: int
    created_at: str


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: bool


class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    mention_count: int


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation_type: str
    evidence_chunk_id: str
    source_filename: str
    snippet: str
    confidence: float


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
