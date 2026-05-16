from hidb.models import User, db


def test_logged_in_user_can_save_theme(client, auth, app):
    auth.login()

    response = client.post(
        "/auth/preferences",
        data={"theme": "light"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 204

    with app.app_context():
        user = User.query.filter_by(username="test").one()
        assert user.preferences["theme"] == "light"

    page = client.get("/items")
    assert b'data-theme = "light"' in page.data or b"dataset.theme = \"light\"" in page.data
    assert b'documentElement.dataset.theme = "light"' in page.data


def test_invalid_theme_rejected(client, auth):
    auth.login()
    response = client.post(
        "/auth/preferences",
        data={"theme": "neon"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400


def test_guest_cannot_save_preferences(client):
    response = client.post(
        "/auth/preferences",
        data={"theme": "light"},
    )
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_logged_in_page_sets_theme_from_preferences(client, auth, app):
    auth.login()
    with app.app_context():
        user = User.query.filter_by(username="test").one()
        user.preferences = {"theme": "light"}
        db.session.commit()

    response = client.get("/items")
    assert b'documentElement.dataset.theme = "light"' in response.data
