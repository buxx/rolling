"""character account id

Revision ID: 60e01a4471ee
Revises: 47837f950128
Create Date: 2022-11-03 14:54:43.767007

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.exc as saexc


# revision identifiers, used by Alembic.
revision = "60e01a4471ee"
down_revision = "47837f950128"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("character", sa.Column("account_id", sa.String(255), nullable=True))
    op.create_foreign_key(None, "character", "account", ["account_id"], ["id"])

    for row in op.get_bind().execute("SELECT id FROM character").all():
        character_id = row[0]
        try:
            account_id = (
                op.get_bind()
                .execute(
                    f"SELECT id FROM account WHERE current_character_id = '{character_id}'",
                )
                .one()
            )[0]
            op.get_bind().execute(
                f"UPDATE character SET account_id='{account_id}' WHERE id = '{character_id}'",
            )
        except saexc.NoResultFound:
            pass


def downgrade():
    op.drop_constraint(None, "character", type_="foreignkey")
    op.drop_column("character", "account_id")
