"""add creation datetime to affinity

Revision ID: be361e493093
Revises: 9118db15d7e5
Create Date: 2022-08-21 21:18:10.614511

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "be361e493093"
down_revision = "9118db15d7e5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "affinity",
        sa.Column(
            "creation_datetime",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("affinity", "creation_datetime")
