"""add avatar

Revision ID: 128be651c40e
Revises: 3317baf5a3f5
Create Date: 2021-10-26 21:28:10.667602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "128be651c40e"
down_revision = "3317baf5a3f5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character", sa.Column("avatar_uuid", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "character",
        sa.Column(
            "avatar_is_validated", sa.Boolean(), nullable=False, server_default="FALSE"
        ),
    )


def downgrade():
    op.drop_column("character", "avatar_is_validated")
    op.drop_column("character", "avatar_uuid")
