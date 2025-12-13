"""add visitors to flash_sales

Revision ID: bfd4527d4297
Revises: c35b6a972b34
Create Date: 2025-12-09 12:07:53.421974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfd4527d4297'
down_revision: Union[str, Sequence[str], None] = 'c35b6a972b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "flash_sales",
        sa.Column("visitors", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("flash_sales", "visitors")
