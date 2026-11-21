"""create session_rate table

Revision ID: b6a71d82f304
Revises: ad8c21f5e9b7
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6a71d82f304"
down_revision: Union[str, Sequence[str], None] = "ad8c21f5e9b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "session_rate" in inspector.get_table_names():
        return

    op.create_table(
        "session_rate",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("id_workout_session", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["id_workout_session"], ["workout_session.id"], name="fk_session_rate_session", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], name="fk_session_rate_user", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="session_rate_pkey"),
        sa.UniqueConstraint("id_workout_session", "user_id", name="uq_session_rate_user"),
        sa.CheckConstraint("rate >= 1 AND rate <= 5", name="chk_session_rate"),
    )
    op.create_index(op.f("ix_session_rate_id"), "session_rate", ["id"], unique=False)
    op.create_index("idx_session_rate_user", "session_rate", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_session_rate_user", table_name="session_rate")
    op.drop_index(op.f("ix_session_rate_id"), table_name="session_rate")
    op.drop_table("session_rate")
