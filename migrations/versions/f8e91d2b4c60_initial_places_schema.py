"""Initial schema with hierarchical places

Revision ID: f8e91d2b4c60
Revises:
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa


revision = "f8e91d2b4c60"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "creator_id",
            "parent_id",
            "name",
            name="uq_place_name_under_parent",
        ),
    )
    op.create_index(op.f("ix_places_creator_id"), "places", ["creator_id"], unique=False)
    op.create_index(op.f("ix_places_parent_id"), "places", ["parent_id"], unique=False)
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("serial_no", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("photo", sa.Text(), nullable=True),
        sa.Column("date_added", sa.DateTime(), nullable=False),
        sa.Column("date_acquired", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_creator_id"), "items", ["creator_id"], unique=False)
    op.create_index(op.f("ix_items_place_id"), "items", ["place_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_items_place_id"), table_name="items")
    op.drop_index(op.f("ix_items_creator_id"), table_name="items")
    op.drop_table("items")
    op.drop_index(op.f("ix_places_parent_id"), table_name="places")
    op.drop_index(op.f("ix_places_creator_id"), table_name="places")
    op.drop_table("places")
    op.drop_table("users")
