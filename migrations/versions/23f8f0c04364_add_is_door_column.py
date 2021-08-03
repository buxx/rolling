"""add is_door column

Revision ID: 23f8f0c04364
Revises: a4e8eba0e077
Create Date: 2021-08-05 12:37:01.596712

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '23f8f0c04364'
down_revision = 'a4e8eba0e077'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('build', sa.Column('is_door', sa.Boolean(), nullable=False, server_default="FALSE"))


def downgrade():
    op.drop_column('build', 'is_door')
