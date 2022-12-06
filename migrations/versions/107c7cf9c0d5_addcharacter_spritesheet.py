"""addcharacter spritesheet

Revision ID: 107c7cf9c0d5
Revises: 4c3f0fadb630
Create Date: 2022-12-06 15:55:17.963427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "107c7cf9c0d5"
down_revision = "4c3f0fadb630"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character", sa.Column("spritesheet_identifiers", sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column("character", "spritesheet_identifiers")
