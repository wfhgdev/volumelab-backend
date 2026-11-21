"""create_mesocycle_table

Revision ID: 64b76c04a31f
Revises: 8b88458469be
Create Date: 2026-11-21 09:13:04.050122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '64b76c04a31f'
down_revision: Union[str, Sequence[str], None] = '8b88458469be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Crear ENUM mesocycle_status si no existe (PostgreSQL)
    if bind.dialect.name == "postgresql":
        mesocycle_status = postgresql.ENUM('PLANIFICADO', 'ACTIVO', 'FINALIZADO', name='mesocycle_status')
        mesocycle_status.create(bind, checkfirst=True)

    # 2. Crear tabla mesocycle si no existe
    tables = inspector.get_table_names()
    if 'mesocycle' not in tables:
        op.create_table(
            'mesocycle',
            sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column(
                'status',
                sa.Enum('PLANIFICADO', 'ACTIVO', 'FINALIZADO', name='mesocycle_status', create_type=False),
                server_default='PLANIFICADO',
                nullable=False
            ),
            sa.CheckConstraint('end_date >= start_date', name='chk_mesocycle_dates'),
            sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name='fk_mesocycle_user', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name='mesocycle_pkey')
        )
        op.create_index('idx_mesocycle_user', 'mesocycle', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'mesocycle' in tables:
        op.drop_index('idx_mesocycle_user', table_name='mesocycle')
        op.drop_table('mesocycle')

    if bind.dialect.name == "postgresql":
        mesocycle_status = postgresql.ENUM('PLANIFICADO', 'ACTIVO', 'FINALIZADO', name='mesocycle_status')
        mesocycle_status.drop(bind, checkfirst=True)
