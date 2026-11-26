"""create weight_history table

Revision ID: c4f19e82a3b1
Revises: 8b88458469be
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f19e82a3b1"
down_revision: Union[str, Sequence[str], None] = "ad8c21f5e9b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().as_sql:
        table_exists = False
        index_exists = False
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        table_exists = "weight_history" in inspector.get_table_names()
        index_exists = (
            table_exists
            and "idx_weight_history_user_date"
            in {index["name"] for index in inspector.get_indexes("weight_history")}
        )

    if not table_exists:
        op.create_table(
            "weight_history",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint("weight_kg > 0", name="chk_weight_kg"),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["app_user.id"],
                name="fk_weight_history_user",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="weight_history_pkey"),
        )

    if not index_exists:
        op.execute(
            "CREATE INDEX idx_weight_history_user_date "
            "ON weight_history (user_id, created_at DESC)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_weight_history_user_date")
    op.drop_table("weight_history")
