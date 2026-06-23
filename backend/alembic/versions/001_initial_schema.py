"""Initial schema with extensions and all tables

Revision ID: 001
Revises:
Create Date: 2026-06-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="employee"),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("azure_oid", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("azure_oid"),
    )

    # Create documents table
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="ready"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create doc_chunks table
    op.create_table(
        "doc_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create HNSW index for embeddings
    op.execute(
        """
        CREATE INDEX doc_chunks_embedding_idx
            ON doc_chunks USING hnsw (embedding vector_cosine_ops);
        """
    )

    # Create query_quota table
    op.create_table(
        "query_quota",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("user_id", "usage_date"),
    )

    # Create audit_log table
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("audit_log")
    op.drop_table("query_quota")
    op.drop_table("doc_chunks")
    op.drop_table("documents")
    op.drop_table("users")

    # Drop extensions
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
