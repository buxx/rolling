"""affinity protectorate

Revision ID: 4c3f0fadb630
Revises: 304b4557269e
Create Date: 2022-11-26 13:36:04.805234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4c3f0fadb630"
down_revision = "304b4557269e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "affinity_protectorate",
        sa.Column("affinity_id", sa.Integer(), nullable=False),
        sa.Column("world_row_i", sa.Integer(), nullable=False),
        sa.Column("world_col_i", sa.Integer(), nullable=False),
        sa.Column("updated_datetime", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["affinity_id"],
            ["affinity.id"],
        ),
        sa.PrimaryKeyConstraint("affinity_id", "world_row_i", "world_col_i"),
    )


def downgrade():
    op.drop_table("affinity_protectorate")
