"""add spawn point

Revision ID: 9118db15d7e5
Revises: 5d6e22b3496d
Create Date: 2022-08-21 21:03:47.479571

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9118db15d7e5"
down_revision = "5d6e22b3496d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "spawn",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("build_id", sa.Integer(), nullable=False),
        sa.Column("affinity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["affinity_id"],
            ["affinity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["build_id"],
            ["build.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("spawn")
