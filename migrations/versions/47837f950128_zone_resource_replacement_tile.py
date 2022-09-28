"""zone resource replacement tile

Revision ID: 47837f950128
Revises: 4b2f5e5df547
Create Date: 2022-09-28 08:58:50.844693

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "47837f950128"
down_revision = "4b2f5e5df547"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "zone_resource",
        sa.Column("replace_by_when_destroyed", sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column("zone_resource", "replace_by_when_destroyed")
