import json


def test_embed_create_place_returns_json(client, auth, app):
    auth.login()

    response = client.post(
        "/places/create?embed=1",
        data={
            "embed": "1",
            "name": "Office",
            "description": "",
            "parent_id": "",
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["ok"] is True
    assert data["label"] == "Office"
    assert isinstance(data["id"], int)


def test_embed_create_place_validation_error(client, auth):
    auth.login()

    response = client.post(
        "/places/create?embed=1",
        data={"embed": "1", "name": "", "parent_id": ""},
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["ok"] is False
    assert "Name is required" in data["html"]


def test_embed_get_returns_form_partial(client, auth):
    auth.login()
    response = client.get("/places/create?embed=1")
    assert response.status_code == 200
    assert b"place-create-form" in response.data
    assert b"<html" not in response.data.lower()
