"""flash sale + price snapshot update

Revision ID: f8e9877e915e
Revises: e1b61009c534
Create Date: 2025-12-05 17:30:23.361268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8e9877e915e'
down_revision: Union[str, Sequence[str], None] = 'e1b61009c534'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    """
    This migration used to create the `price_snapshots` table and add columns,
    but those were already created by earlier code (Base.metadata.create_all).

    So now it's a NO-OP, just here to advance Alembic's version stamp.
    """
    pass


def downgrade():
    """
    Also make downgrade a NO-OP for safety.
    If you ever need to drop price_snapshots, do it in a new migration.
    """
    pass