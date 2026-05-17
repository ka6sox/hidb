"""Item photos, units, drop items.photo

Revision ID: c4a8e1f03b2d
Revises: b7e2f4a91c3d
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa


revision = "c4a8e1f03b2d"
down_revision = "b7e2f4a91c3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "item_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_item_photos_item_id"), "item_photos", ["item_id"], unique=False
    )

    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unit_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_items_unit_id", "units", ["unit_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index(batch_op.f("ix_items_unit_id"), ["unit_id"], unique=False)

    op.execute(
        """
        INSERT INTO item_photos (item_id, filename, sort_order, created_at)
        SELECT id, photo, 0, date_added
        FROM items
        WHERE photo IS NOT NULL AND photo != ''
        """
    )

    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_column("photo")


def downgrade():
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("photo", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE items
        SET photo = (
            SELECT filename FROM item_photos
            WHERE item_photos.item_id = items.id
            ORDER BY sort_order ASC
            LIMIT 1
        )
        """
    )

    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_items_unit_id"))
        batch_op.drop_constraint("fk_items_unit_id", type_="foreignkey")
        batch_op.drop_column("unit_id")

    op.drop_index(op.f("ix_item_photos_item_id"), table_name="item_photos")
    op.drop_table("item_photos")
    op.drop_table("units")
