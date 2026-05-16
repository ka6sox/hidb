"""Add user preferences JSON column

Revision ID: b7e2f4a91c3d
Revises: a3f8c1d92b4e
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa


revision = "b7e2f4a91c3d"
down_revision = "a3f8c1d92b4e"
branch_labels = None
depends_on = None

DEFAULT_PREFERENCES = '{"theme": "dark"}'


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("preferences", sa.JSON(), nullable=True))

    op.get_bind().execute(
        sa.text("UPDATE users SET preferences = :prefs WHERE preferences IS NULL"),
        {"prefs": DEFAULT_PREFERENCES},
    )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("preferences")
