"""multiple token

Revision ID: 7951cabb06e4
Revises: c40fb3e13288
Create Date: 2022-08-31 10:44:26.502401

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7951cabb06e4"
down_revision = "c40fb3e13288"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_token",
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("authentication_token", sa.String(length=32), nullable=False),
        sa.Column("authentication_expire", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["account.id"],
        ),
        sa.PrimaryKeyConstraint("authentication_token"),
    )
    op.drop_column("account", "authentication_expire")
    op.drop_column("account", "authentication_token")


def downgrade():
    op.add_column(
        "account",
        sa.Column(
            "authentication_token",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "account",
        sa.Column(
            "authentication_expire", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.drop_table("account_token")
