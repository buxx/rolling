"""add door table

Revision ID: a4e8eba0e077
Revises: c852cc772534
Create Date: 2021-08-02 08:45:21.361262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4e8eba0e077'
down_revision = 'c852cc772534'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'door',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('build_id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.String(length=255), nullable=False),
        sa.Column('mode', sa.Enum('CLOSED', 'CLOSED_EXCEPT_FOR', name='door__mode'), nullable=False),
        sa.Column('affinity_ids', sa.Text(), server_default='[]', nullable=False),
        sa.Column('updated_datetime', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['character_id'], ['character.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('build_id', 'character_id', name='door_unique')
    )


def downgrade():
    op.drop_table('door')
