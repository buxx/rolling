"""add farming columns

Revision ID: 6d4fcb24f035
Revises: 23f8f0c04364
Create Date: 2021-08-12 11:54:13.225600

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d4fcb24f035'
down_revision = '23f8f0c04364'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('build', sa.Column('seeded_with', sa.String(length=255), nullable=True))
    op.add_column('build', sa.Column('grow_progress', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('build', 'grow_progress')
    op.drop_column('build', 'seeded_with')
