"""Add place is_private flag

Revision ID: a3f8c1d92b4e
Revises: 7b4c2d9f1a6e
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa


revision = "a3f8c1d92b4e"
down_revision = "7b4c2d9f1a6e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("places") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_private",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade():
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_column("is_private")
