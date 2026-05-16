import os
import tempfile
from datetime import datetime

import pytest
from werkzeug.security import generate_password_hash

from hidb import create_app
from hidb.models import User, db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "CSRF_ENABLED": False,
            "SESSION_COOKIE_SECURE": False,
        }
    )
    with app.app_context():
        from flask_migrate import upgrade

        upgrade()
        db.session.add(
            User(
                username="test",
                password=generate_password_hash("test"),
                role="owner",
                password_updated_at=datetime.utcnow(),
                preferences={"theme": "dark"},
            ),
        )
        db.session.add(
            User(
                username="other",
                password=generate_password_hash("other"),
                role="co_owner",
                password_updated_at=datetime.utcnow(),
                preferences={"theme": "dark"},
            ),
        )
        db.session.commit()

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username="test", password="test"):
        return self._client.post(
            "/auth/login",
            data={"username": username, "password": password},
        )

    def logout(self):
        return self._client.post("/auth/logout")


@pytest.fixture
def auth(client):
    return AuthActions(client)
