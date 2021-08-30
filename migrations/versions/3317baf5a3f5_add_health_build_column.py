"""add health build column

Revision ID: 3317baf5a3f5
Revises: 6d4fcb24f035
Create Date: 2021-08-31 10:36:15.541863

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3317baf5a3f5'
down_revision = '6d4fcb24f035'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('build', sa.Column('health', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('build', 'health')
