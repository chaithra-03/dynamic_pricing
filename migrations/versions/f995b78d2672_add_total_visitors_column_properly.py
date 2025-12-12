from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f995b78d2672"
down_revision: Union[str, Sequence[str], None] = "f8e9877e915e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    pass           # We do NOT drop the default; having default 0 is completely fine.


def downgrade():
    pass