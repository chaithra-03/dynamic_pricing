"""add total_visitors to flash_sales

Revision ID: 5fd8bdd4ce15
Revises: f8e9877e915e
Create Date: 2025-12-09 11:01:27.278216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fd8bdd4ce15'
down_revision: Union[str, Sequence[str], None] = 'f8e9877e915e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
