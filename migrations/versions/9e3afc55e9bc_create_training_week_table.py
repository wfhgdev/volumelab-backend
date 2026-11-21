"""create_training_week_table

Revision ID: 9e3afc55e9bc
Revises: 64b76c04a31f
Create Date: 2026-11-21 15:36:06.623376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e3afc55e9bc'
down_revision: Union[str, Sequence[str], None] = '64b76c04a31f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'training_week' not in tables:
        op.create_table(
            'training_week',
            sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column('mesocycle_id', sa.BigInteger(), nullable=False),
            sa.Column('week_order', sa.Integer(), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.CheckConstraint('week_order >= 1', name='chk_training_week_order'),
            sa.CheckConstraint('end_date >= start_date', name='chk_training_week_dates'),
            sa.ForeignKeyConstraint(['mesocycle_id'], ['mesocycle.id'], name='fk_training_week_mesocycle', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name='training_week_pkey'),
            sa.UniqueConstraint('mesocycle_id', 'week_order', name='uq_training_week_order')
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'training_week' in tables:
        op.drop_table('training_week')
