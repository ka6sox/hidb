import click
from flask import current_app
from hidb.models import db


def init_db():
    """Initialize the database by creating all tables."""
    db.create_all()


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    click.echo('Initialized the database.')


def init_app(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    app.cli.add_command(init_db_command)
