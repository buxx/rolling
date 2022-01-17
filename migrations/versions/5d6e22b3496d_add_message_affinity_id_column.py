"""add message affinity id column

Revision ID: 5d6e22b3496d
Revises: 128be651c40e
Create Date: 2022-01-17 18:52:15.561012

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5d6e22b3496d"
down_revision = "128be651c40e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("message", sa.Column("affinity_id", sa.String(), nullable=True))


def downgrade():
    op.drop_column("message", "affinity_id")
