"""create plant operations schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-21
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("equipment", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_equipment", "documents", ["equipment"])
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536)),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_table(
        "equipment_alarms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("equipment", sa.String(length=120), nullable=False),
        sa.Column("alarm_code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("unit", sa.String(length=30)),
    )
    op.create_index("ix_equipment_alarms_equipment", "equipment_alarms", ["equipment"])
    op.create_index("ix_equipment_alarms_alarm_code", "equipment_alarms", ["alarm_code"])
    op.create_index("ix_equipment_alarms_occurred_at", "equipment_alarms", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("equipment_alarms")
    op.drop_table("document_chunks")
    op.drop_table("documents")
