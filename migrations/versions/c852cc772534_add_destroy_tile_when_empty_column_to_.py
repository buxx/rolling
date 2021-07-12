"""add destroy_tile_when_empty column to zone resource table

Revision ID: c852cc772534
Revises: 884646935cc4
Create Date: 2021-07-13 14:47:27.522080

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c852cc772534'
down_revision = '884646935cc4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('zone_resource', sa.Column('destroy_tile_when_empty', sa.Boolean(), nullable=False, server_default='TRUE'))


def downgrade():
    op.drop_column('zone_resource', 'destroy_tile_when_empty')
