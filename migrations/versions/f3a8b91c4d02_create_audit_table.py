"""create audit table

Revision ID: f3a8b91c4d02
Revises: ad8c21f5e9b7
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f3a8b91c4d02"
down_revision: Union[str, Sequence[str], None] = "ad8c21f5e9b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_offline = op.get_context().as_sql
    if is_offline:
        table_exists = False
        existing_indexes: set[str] = set()
        is_postgres = True
    else:
        bind = op.get_bind()
        is_postgres = bind.dialect.name == "postgresql"
        inspector = sa.inspect(bind)
        table_exists = "audit" in inspector.get_table_names()
        existing_indexes = (
            {idx["name"] for idx in inspector.get_indexes("audit")}
            if table_exists
            else set()
        )

    if is_postgres:
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE audit_action AS ENUM ('INSERT', 'UPDATE', 'DELETE', 'EXPORT');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )

    audit_action_type = (
        postgresql.ENUM(
            "INSERT",
            "UPDATE",
            "DELETE",
            "EXPORT",
            name="audit_action",
            create_type=False,
        )
        if is_postgres
        else sa.Enum("INSERT", "UPDATE", "DELETE", "EXPORT", name="audit_action")
    )

    if not table_exists:
        op.create_table(
            "audit",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=True),
            sa.Column("entity", sa.String(length=60), nullable=False),
            sa.Column("record_id", sa.String(length=60), nullable=False),
            sa.Column("action", audit_action_type, nullable=False),
            sa.Column("endpoint", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["app_user.id"],
                name="fk_audit_user",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="audit_pkey"),
        )

    if "idx_audit_user" not in existing_indexes:
        op.execute("CREATE INDEX idx_audit_user ON audit (user_id)")
    if "idx_audit_entity_record" not in existing_indexes:
        op.execute("CREATE INDEX idx_audit_entity_record ON audit (entity, record_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_entity_record")
    op.execute("DROP INDEX IF EXISTS idx_audit_user")
    op.drop_table("audit")
    op.execute("DROP TYPE IF EXISTS audit_action")
