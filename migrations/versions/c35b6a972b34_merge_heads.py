"""merge heads

Revision ID: c35b6a972b34
Revises: 5fd8bdd4ce15, f995b78d2672
Create Date: 2025-12-09 12:06:56.791333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c35b6a972b34'
down_revision: Union[str, Sequence[str], None] = ('5fd8bdd4ce15', 'f995b78d2672')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
