"""Add user roles and account state

Revision ID: 7b4c2d9f1a6e
Revises: f8e91d2b4c60
Create Date: 2026-05-13

"""
from alembic import op
import sqlalchemy as sa


revision = "7b4c2d9f1a6e"
down_revision = "f8e91d2b4c60"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=32),
                nullable=False,
                server_default="reader",
            )
        )
        batch_op.add_column(
            sa.Column("editor_for_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch_op.add_column(
            sa.Column("role_updated_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("role_updated_by_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("password_updated_at", sa.DateTime(), nullable=True)
        )
        batch_op.create_index(
            op.f("ix_users_editor_for_id"),
            ["editor_for_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_users_editor_for_id_users",
            "users",
            ["editor_for_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_users_role_updated_by_id_users",
            "users",
            ["role_updated_by_id"],
            ["id"],
        )

    connection = op.get_bind()
    first_user_id = connection.execute(sa.text("SELECT MIN(id) FROM users")).scalar()
    if first_user_id is not None:
        connection.execute(
            sa.text("UPDATE users SET role = 'owner' WHERE id = :user_id"),
            {"user_id": first_user_id},
        )

    op.create_index(
        "uq_users_single_owner",
        "users",
        ["role"],
        unique=True,
        sqlite_where=sa.text("role = 'owner'"),
        postgresql_where=sa.text("role = 'owner'"),
    )


def downgrade():
    op.drop_index("uq_users_single_owner", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(
            "fk_users_role_updated_by_id_users",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_users_editor_for_id_users",
            type_="foreignkey",
        )
        batch_op.drop_index(op.f("ix_users_editor_for_id"))
        batch_op.drop_column("password_updated_at")
        batch_op.drop_column("role_updated_by_id")
        batch_op.drop_column("role_updated_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("editor_for_id")
        batch_op.drop_column("role")
