"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-15 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_filename", sa.String(length=1024), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_hash", "namespace", name="uq_documents_hash_namespace"),
    )
    op.create_index(op.f("ix_documents_namespace"), "documents", ["namespace"], unique=False)

    op.create_table(
        "namespace_access",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("permission", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "namespace", name="uq_namespace_access_user_namespace"),
    )
    op.create_index(
        op.f("ix_namespace_access_namespace"),
        "namespace_access",
        ["namespace"],
        unique=False,
    )
    op.create_index(
        op.f("ix_namespace_access_user_id"),
        "namespace_access",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eval_runs_namespace"), "eval_runs", ["namespace"], unique=False)

    op.create_table(
        "guardrail_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_guardrail_events_check_name"),
        "guardrail_events",
        ["check_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_guardrail_events_trace_id"),
        "guardrail_events",
        ["trace_id"],
        unique=False,
    )

    op.create_table(
        "cost_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("embedding_tokens", sa.Integer(), nullable=False),
        sa.Column("chat_cost_usd", sa.Float(), nullable=False),
        sa.Column("embedding_cost_usd", sa.Float(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_events_trace_id"), "cost_events", ["trace_id"], unique=False)

    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chunks_document_id"), "chunks", ["document_id"], unique=False)

    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("generated_answer", sa.Text(), nullable=False),
        sa.Column("citation_validity_v0", sa.Float(), nullable=False),
        sa.Column("keyword_overlap_v0", sa.Float(), nullable=False),
        sa.Column("context_recall_v0", sa.Float(), nullable=False),
        sa.Column("retrieval_hit_v0", sa.Boolean(), nullable=False),
        sa.Column("failure_type", sa.String(length=64), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["eval_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eval_results_run_id"), "eval_results", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_eval_results_run_id"), table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index(op.f("ix_chunks_document_id"), table_name="chunks")
    op.drop_table("chunks")
    op.drop_index(op.f("ix_cost_events_trace_id"), table_name="cost_events")
    op.drop_table("cost_events")
    op.drop_index(op.f("ix_guardrail_events_trace_id"), table_name="guardrail_events")
    op.drop_index(op.f("ix_guardrail_events_check_name"), table_name="guardrail_events")
    op.drop_table("guardrail_events")
    op.drop_index(op.f("ix_eval_runs_namespace"), table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index(op.f("ix_namespace_access_user_id"), table_name="namespace_access")
    op.drop_index(op.f("ix_namespace_access_namespace"), table_name="namespace_access")
    op.drop_table("namespace_access")
    op.drop_index(op.f("ix_documents_namespace"), table_name="documents")
    op.drop_table("documents")
