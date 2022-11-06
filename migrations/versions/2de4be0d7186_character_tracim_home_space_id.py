"""character tracim home space id

Revision ID: 2de4be0d7186
Revises: e076fa26976b
Create Date: 2022-11-06 18:40:44.167888

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2de4be0d7186"
down_revision = "e076fa26976b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character", sa.Column("tracim_home_space_id", sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column("character", "tracim_home_space_id")
