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
    pass

def downgrade():
    pass