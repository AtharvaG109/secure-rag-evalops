"""collections and retention

Revision ID: 0002_collections
Revises: 0001_initial
Create Date: 2026-05-16 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_collections"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("namespace", "name", name="uq_collections_namespace_name"),
    )
    op.create_index(op.f("ix_collections_namespace"), "collections", ["namespace"], unique=False)
    op.add_column("documents", sa.Column("collection_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(None, "documents", "collections", ["collection_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(None, "documents", type_="foreignkey")
    op.drop_column("documents", "collection_id")
    op.drop_index(op.f("ix_collections_namespace"), table_name="collections")
    op.drop_table("collections")
