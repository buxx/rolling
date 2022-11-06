"""character tracim password

Revision ID: 8bf5d61d2bf5
Revises: 60e01a4471ee
Create Date: 2022-11-03 20:18:50.430025

"""
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8bf5d61d2bf5"
down_revision = "60e01a4471ee"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character", sa.Column("tracim_password", sa.String(255), nullable=True)
    )
    for row in op.get_bind().execute("SELECT id FROM character").all():
        character_id = row[0]
        op.get_bind().execute(
            f"UPDATE character SET tracim_password='{uuid.uuid4().hex}' WHERE id = '{character_id}'",
        )


def downgrade():
    op.drop_column("character", "tracim_password")
