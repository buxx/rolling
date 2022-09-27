"""skill counter as numeric

Revision ID: 4b2f5e5df547
Revises: 7951cabb06e4
Create Date: 2022-09-27 17:23:41.888878

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4b2f5e5df547"
down_revision = "7951cabb06e4"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "character_skill",
        "counter",
        type_=sa.Numeric(10, 4),
        nullable=False,
    )


def downgrade():
    op.alter_column(
        "character_skill",
        "counter",
        existing_type=sa.Integer(),
        nullable=False,
    )
