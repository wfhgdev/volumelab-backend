"""merge migration heads

Revision ID: b04e53ddb8e3
Revises: 9e3afc55e9bc, b6a71d82f304, c4f19e82a3b1, e7b92c431d01
Create Date: 2026-11-21 23:36:29.538384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b04e53ddb8e3'
down_revision: Union[str, Sequence[str], None] = ('9e3afc55e9bc', 'c4f19e82a3b1', 'e7b92c431d01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
