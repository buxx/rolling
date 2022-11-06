"""affinity space id

Revision ID: 304b4557269e
Revises: 2de4be0d7186
Create Date: 2022-11-09 12:14:02.715509

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "304b4557269e"
down_revision = "2de4be0d7186"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("affinity", sa.Column("tracim_space_id", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("affinity", "tracim_space_id")
