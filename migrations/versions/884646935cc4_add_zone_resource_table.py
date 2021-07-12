"""add zone resource table

Revision ID: 884646935cc4
Revises: acf7115ac89d
Create Date: 2021-07-13 13:44:23.539547

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '884646935cc4'
down_revision = 'acf7115ac89d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('zone_resource',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('world_col_i', sa.Integer(), nullable=False),
    sa.Column('world_row_i', sa.Integer(), nullable=False),
    sa.Column('zone_col_i', sa.Integer(), nullable=False),
    sa.Column('zone_row_i', sa.Integer(), nullable=False),
    sa.Column('resource_id', sa.String(length=255), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=12, scale=6, asdecimal=False), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('world_col_i', 'world_row_i', 'zone_col_i', 'zone_row_i', 'resource_id', name='zone_resource_unique')
    )


def downgrade():
    op.drop_table('zone_resource')
