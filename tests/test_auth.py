import pytest
from flask import g, session
from werkzeug.security import generate_password_hash

from hidb import create_app
from hidb.models import db, User


def make_isolated_app(tmp_path, csrf_enabled=False):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite'}",
            "CSRF_ENABLED": csrf_enabled,
            "SESSION_COOKIE_SECURE": False,
        }
    )
    with app.app_context():
        from flask_migrate import upgrade

        upgrade()
    return app


def test_register(client, app):
    assert client.get("/auth/register").status_code == 200
    response = client.post(
        "/auth/register",
        data={"username": "newuser", "password": "password123"},
    )
    assert response.headers["Location"].endswith("/auth/login")

    with app.app_context():
        user = User.query.filter_by(username="newuser").first()
        assert user is not None
        assert user.role == "reader"


def test_first_registered_user_becomes_owner(tmp_path):
    app = make_isolated_app(tmp_path)
    client = app.test_client()

    client.post(
        "/auth/register",
        data={"username": "first", "password": "password123"},
    )
    client.post(
        "/auth/register",
        data={"username": "second", "password": "password123"},
    )

    with app.app_context():
        assert User.query.filter_by(username="first").one().role == "owner"
        assert User.query.filter_by(username="second").one().role == "reader"


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("", "", b"Username is required."),
        ("a", "", b"Password is required."),
        ("a", "short", b"at least 8 characters"),
        ("test", "password123", b"already registered"),
    ),
)
def test_register_validate_input(client, username, password, message):
    response = client.post(
        "/auth/register",
        data={"username": username, "password": password},
    )
    assert message in response.data


def test_login(client, auth):
    assert client.get("/auth/login").status_code == 200
    response = auth.login()
    assert response.headers["Location"] in ("/", "/items")

    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user.username == "test"


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("a", "test", b"Incorrect username or password."),
        ("test", "a", b"Incorrect username or password."),
    ),
)
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data


def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert "user_id" not in session


def test_logout_get_not_allowed(client, auth):
    auth.login()
    assert client.get("/auth/logout").status_code == 405


def test_inactive_user_cannot_login(client, app):
    with app.app_context():
        user = User.query.filter_by(username="other").one()
        user.is_active = False
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "other", "password": "other"},
    )
    assert b"Incorrect username or password." in response.data


def test_owner_can_reset_password(client, auth):
    auth.login()
    response = client.post(
        "/auth/users/2/password",
        data={
            "password": "newpassword",
            "confirm_password": "newpassword",
        },
    )
    assert response.headers["Location"].endswith("/auth/users")

    auth.logout()
    response = auth.login("other", "newpassword")
    assert response.headers["Location"] in ("/", "/items")


def test_non_owner_cannot_reset_password(client, auth):
    auth.login("other", "other")
    response = client.post(
        "/auth/users/1/password",
        data={
            "password": "newpassword",
            "confirm_password": "newpassword",
        },
    )
    assert response.status_code == 403


def test_csrf_rejects_missing_token(tmp_path):
    app = make_isolated_app(tmp_path, csrf_enabled=True)
    client = app.test_client()

    response = client.post(
        "/auth/register",
        data={"username": "first", "password": "password123"},
    )

    assert response.status_code == 400


def test_owner_can_create_user(client, auth, app):
    auth.login()
    response = client.post(
        "/auth/users/create",
        data={
            "username": "neweditor",
            "password": "password123",
            "confirm_password": "password123",
            "role": "editor",
            "editor_for_id": "1",
        },
    )
    assert response.headers["Location"].endswith("/auth/users")

    auth.logout()
    login = auth.login("neweditor", "password123")
    assert login.headers["Location"] in ("/", "/items")

    with app.app_context():
        user = User.query.filter_by(username="neweditor").one()
        assert user.role == "editor"
        assert user.editor_for_id == 1


def test_co_owner_can_create_reader_and_editor(client, auth, app):
    auth.login("other", "other")

    reader = client.post(
        "/auth/users/create",
        data={
            "username": "line_reader",
            "password": "password123",
            "confirm_password": "password123",
            "role": "reader",
        },
    )
    assert reader.headers["Location"].endswith("/auth/users")

    editor = client.post(
        "/auth/users/create",
        data={
            "username": "line_editor",
            "password": "password123",
            "confirm_password": "password123",
            "role": "editor",
        },
    )
    assert editor.headers["Location"].endswith("/auth/users")

    with app.app_context():
        assert User.query.filter_by(username="line_reader").one().role == "reader"
        editor_user = User.query.filter_by(username="line_editor").one()
        assert editor_user.role == "editor"
        assert editor_user.editor_for_id == 2


def test_co_owner_users_page_lists_all_users(client, auth, app):
    auth.login("other", "other")
    with app.app_context():
        db.session.add(
            User(
                username="other_line_editor",
                password=generate_password_hash("password123"),
                role="editor",
                editor_for_id=1,
                is_active=True,
                password_updated_at=User.query.get(1).password_updated_at,
            ),
        )
        db.session.commit()

    response = client.get("/auth/users")
    assert response.status_code == 200
    assert b"test" in response.data
    assert b"other" in response.data
    assert b"other_line_editor" in response.data


def test_co_owner_cannot_create_co_owner(client, auth):
    auth.login("other", "other")
    response = client.post(
        "/auth/users/create",
        data={
            "username": "bad_co",
            "password": "password123",
            "confirm_password": "password123",
            "role": "co_owner",
        },
    )
    assert b"Invalid role." in response.data


def test_csrf_accepts_valid_token(tmp_path):
    app = make_isolated_app(tmp_path, csrf_enabled=True)
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["_csrf_token"] = "known-token"
    response = client.post(
        "/auth/register",
        data={
            "_csrf_token": "known-token",
            "username": "first",
            "password": "password123",
        },
    )

    assert response.headers["Location"].endswith("/auth/login")
