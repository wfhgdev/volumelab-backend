"""merge heads for workout set

Revision ID: 704390f96f9b
Revises: a9d1b6c2e730, c9f4a7b2d8e1, d3c8a51f9072, f2a7c8e9d410
Create Date: 2026-11-23
"""

from typing import Sequence, Union

from alembic import op

revision: str = "704390f96f9b"
down_revision: Union[str, Sequence[str], None] = (
    "a9d1b6c2e730",
    "b6a71d82f304",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
