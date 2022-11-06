"""character tracim id

Revision ID: e076fa26976b
Revises: 8bf5d61d2bf5
Create Date: 2022-11-04 17:53:37.447009

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e076fa26976b"
down_revision = "8bf5d61d2bf5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("character", sa.Column("tracim_user_id", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("character", "tracim_user_id")
