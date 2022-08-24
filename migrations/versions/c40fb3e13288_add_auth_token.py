"""add auth token

Revision ID: c40fb3e13288
Revises: be361e493093
Create Date: 2022-08-24 12:31:06.188379

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c40fb3e13288"
down_revision = "be361e493093"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "account",
        sa.Column("authentication_token", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "account", sa.Column("authentication_expire", sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column("account", "authentication_expire")
    op.drop_column("account", "authentication_token")
