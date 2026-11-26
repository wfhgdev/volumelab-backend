"""create workout_rate table

Revision ID: e7b92c431d01
Revises: 8b88458469be
Create Date: 2026-11-20 14:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b92c431d01'
down_revision: Union[str, Sequence[str], None] = 'f2a7c8e9d410'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workout_rate',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('id_workout', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('rate', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['id_workout'], ['workout.id'], name='fk_workout_rate_workout', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='fk_workout_rate_user', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='workout_rate_pkey'),
        sa.UniqueConstraint('id_workout', 'user_id', name='uq_workout_rate_user'),
        sa.CheckConstraint('rate >= 1 AND rate <= 5', name='chk_workout_rate'),
    )
    op.create_index(op.f('ix_workout_rate_id'), 'workout_rate', ['id'], unique=False)
    op.create_index('idx_workout_rate_user', 'workout_rate', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_workout_rate_user', table_name='workout_rate')
    op.drop_index(op.f('ix_workout_rate_id'), table_name='workout_rate')
    op.drop_table('workout_rate')
