"""RAG ingestion foundation: background ingestion, parent-child chunks, OCR status, embedding metadata.

Revision ID: 20260706_0002
Revises: 20260706_0001
Create Date: 2026-07-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260706_0002"
down_revision = "20260706_0001"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in sa.inspect(bind).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {idx["name"] for idx in sa.inspect(bind).get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {fk.get("name") for fk in sa.inspect(bind).get_foreign_keys(table_name) if fk.get("name")}


def upgrade() -> None:
    # The initial migration still uses Base.metadata.create_all. On a fresh DB it
    # creates the current model shape before this revision runs, so every add is
    # guarded. On an older DB where 0001 is already applied, these operations add
    # the missing formal schema changes.
    document_cols = _columns("documents")
    with op.batch_alter_table("documents") as batch_op:
        if "ocr_status" not in document_cols:
            batch_op.add_column(
                sa.Column("ocr_status", sa.String(32), nullable=False, server_default="not-required")
            )
        if "is_usable" not in document_cols:
            batch_op.add_column(
                sa.Column("is_usable", sa.Integer(), nullable=False, server_default="0")
            )

    chunk_cols = _columns("document_chunks")
    chunk_fks = _foreign_keys("document_chunks")
    with op.batch_alter_table("document_chunks") as batch_op:
        if "parent_id" not in chunk_cols:
            batch_op.add_column(sa.Column("parent_id", sa.String(32), nullable=True))
        if "chunk_type" not in chunk_cols:
            batch_op.add_column(sa.Column("chunk_type", sa.String(32), nullable=False, server_default="child"))
        if "heading_path" not in chunk_cols:
            batch_op.add_column(sa.Column("heading_path", sa.String(512), nullable=False, server_default=""))
        if "page_start" not in chunk_cols:
            batch_op.add_column(sa.Column("page_start", sa.Integer(), nullable=True))
        if "page_end" not in chunk_cols:
            batch_op.add_column(sa.Column("page_end", sa.Integer(), nullable=True))
        if "source_method" not in chunk_cols:
            batch_op.add_column(sa.Column("source_method", sa.String(32), nullable=False, server_default="native_unknown"))
        if "content_hash" not in chunk_cols:
            batch_op.add_column(sa.Column("content_hash", sa.String(64), nullable=False, server_default=""))
        if "fk_document_chunks_parent_id" not in chunk_fks:
            batch_op.create_foreign_key(
                "fk_document_chunks_parent_id",
                "document_chunks",
                ["parent_id"],
                ["id"],
            )

    chunk_indexes = _indexes("document_chunks")
    with op.batch_alter_table("document_chunks") as batch_op:
        if "ix_document_chunks_document_id" not in chunk_indexes:
            batch_op.create_index("ix_document_chunks_document_id", ["document_id"])
        if "ix_document_chunks_parent_id" not in chunk_indexes:
            batch_op.create_index("ix_document_chunks_parent_id", ["parent_id"])
        if "ix_document_chunks_chunk_type" not in chunk_indexes:
            batch_op.create_index("ix_document_chunks_chunk_type", ["chunk_type"])

    job_indexes = _indexes("ingestion_jobs")
    with op.batch_alter_table("ingestion_jobs") as batch_op:
        if "ix_ingestion_jobs_document_id" not in job_indexes:
            batch_op.create_index("ix_ingestion_jobs_document_id", ["document_id"])


def downgrade() -> None:
    chunk_indexes = _indexes("document_chunks")
    chunk_cols = _columns("document_chunks")
    chunk_fks = _foreign_keys("document_chunks")
    with op.batch_alter_table("document_chunks") as batch_op:
        if "ix_document_chunks_chunk_type" in chunk_indexes:
            batch_op.drop_index("ix_document_chunks_chunk_type")
        if "ix_document_chunks_parent_id" in chunk_indexes:
            batch_op.drop_index("ix_document_chunks_parent_id")
        if "ix_document_chunks_document_id" in chunk_indexes:
            batch_op.drop_index("ix_document_chunks_document_id")
        if "fk_document_chunks_parent_id" in chunk_fks:
            batch_op.drop_constraint("fk_document_chunks_parent_id", type_="foreignkey")
        for column_name in (
            "content_hash",
            "source_method",
            "page_end",
            "page_start",
            "heading_path",
            "chunk_type",
            "parent_id",
        ):
            if column_name in chunk_cols:
                batch_op.drop_column(column_name)

    document_cols = _columns("documents")
    with op.batch_alter_table("documents") as batch_op:
        if "is_usable" in document_cols:
            batch_op.drop_column("is_usable")
        if "ocr_status" in document_cols:
            batch_op.drop_column("ocr_status")

    job_indexes = _indexes("ingestion_jobs")
    with op.batch_alter_table("ingestion_jobs") as batch_op:
        if "ix_ingestion_jobs_document_id" in job_indexes:
            batch_op.drop_index("ix_ingestion_jobs_document_id")