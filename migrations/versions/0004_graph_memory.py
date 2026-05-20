"""graph memory tables

Revision ID: 0004_graph_memory
Revises: 0003_production_hardening
Create Date: 2026-05-17 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_graph_memory"
down_revision: str | None = "0003_production_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("namespace", "normalized_name", name="uq_entities_namespace_name"),
    )
    op.create_index(op.f("ix_entities_namespace"), "entities", ["namespace"], unique=False)
    op.create_table(
        "entity_mentions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("mention_text", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_id", "chunk_id", name="uq_entity_mentions_entity_chunk"),
    )
    op.create_index(
        op.f("ix_entity_mentions_chunk_id"),
        "entity_mentions",
        ["chunk_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_mentions_document_id"),
        "entity_mentions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_mentions_entity_id"),
        "entity_mentions",
        ["entity_id"],
        unique=False,
    )
    op.create_table(
        "entity_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("source_entity_id", sa.String(length=36), nullable=False),
        sa.Column("target_entity_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_chunk_id", sa.String(length=36), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evidence_chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "namespace",
            "source_entity_id",
            "target_entity_id",
            "relation_type",
            "evidence_chunk_id",
            name="uq_entity_relations_evidence",
        ),
    )
    op.create_index(
        op.f("ix_entity_relations_namespace"),
        "entity_relations",
        ["namespace"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_relations_relation_type"),
        "entity_relations",
        ["relation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_relations_source_entity_id"),
        "entity_relations",
        ["source_entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_relations_target_entity_id"),
        "entity_relations",
        ["target_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_entity_relations_target_entity_id"), table_name="entity_relations")
    op.drop_index(op.f("ix_entity_relations_source_entity_id"), table_name="entity_relations")
    op.drop_index(op.f("ix_entity_relations_relation_type"), table_name="entity_relations")
    op.drop_index(op.f("ix_entity_relations_namespace"), table_name="entity_relations")
    op.drop_table("entity_relations")
    op.drop_index(op.f("ix_entity_mentions_entity_id"), table_name="entity_mentions")
    op.drop_index(op.f("ix_entity_mentions_document_id"), table_name="entity_mentions")
    op.drop_index(op.f("ix_entity_mentions_chunk_id"), table_name="entity_mentions")
    op.drop_table("entity_mentions")
    op.drop_index(op.f("ix_entities_namespace"), table_name="entities")
    op.drop_table("entities")
