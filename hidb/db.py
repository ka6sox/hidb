import click
from flask import current_app
from sqlalchemy import text

from hidb.models import db


def init_db():
    """Apply the latest migration (requires application context)."""
    from flask_migrate import upgrade

    upgrade()


@click.command('init-db')
def init_db_command():
    """Drop all tables and re-apply migrations from scratch (destructive)."""
    from flask_migrate import upgrade

    db.drop_all()
    db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
    db.session.commit()
    upgrade()
    click.echo('Initialized the database.')


def init_app(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    app.cli.add_command(init_db_command)
