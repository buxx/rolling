"""spritesheet is set

Revision ID: 50686e99331f
Revises: 8f7724afdfe0
Create Date: 2022-12-12 14:48:48.885896

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "50686e99331f"
down_revision = "8f7724afdfe0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character",
        sa.Column(
            "spritesheet_set",
            sa.Boolean(),
            nullable=False,
            server_default="FALSE",
        ),
    )


def downgrade():
    op.drop_column("character", "spritesheet_set")
