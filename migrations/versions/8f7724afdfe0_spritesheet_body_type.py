"""spritesheet body type

Revision ID: 8f7724afdfe0
Revises: 107c7cf9c0d5
Create Date: 2022-12-12 14:25:08.517601

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f7724afdfe0"
down_revision = "107c7cf9c0d5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character",
        sa.Column("spritesheet_body_type", sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column("character", "spritesheet_body_type")
