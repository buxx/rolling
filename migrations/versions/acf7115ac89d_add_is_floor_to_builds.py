"""add is_floor to builds

Revision ID: acf7115ac89d
Revises: 
Create Date: 2021-07-12 18:50:09.900939

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'acf7115ac89d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('build', sa.Column('is_floor', sa.Boolean(), nullable=False, server_default="FALSE"))


def downgrade():
    op.drop_column('build', 'is_floor')
