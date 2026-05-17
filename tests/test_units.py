from hidb.models import Item, Place, Unit, db


def test_embed_create_unit_returns_json(client, auth, app):
    auth.login()

    response = client.post(
        "/units/create?embed=1",
        data={"name": "Rolls", "embed": "1"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["label"] == "rolls"

    with app.app_context():
        assert Unit.query.filter_by(name="rolls").one() is not None


def test_duplicate_unit_name_returns_existing(client, auth, app):
    auth.login()

    first = client.post(
        "/units/create?embed=1",
        data={"name": "cases", "embed": "1"},
        headers={"Accept": "application/json"},
    )
    second = client.post(
        "/units/create?embed=1",
        data={"name": "Cases", "embed": "1"},
        headers={"Accept": "application/json"},
    )
    assert first.get_json()["id"] == second.get_json()["id"]

    with app.app_context():
        assert Unit.query.filter_by(name="cases").count() == 1


def test_item_with_unit_displays_qty(client, auth, app):
    auth.login()

    with app.app_context():
        place = Place(name="Garage", creator_id=1)
        db.session.add(place)
        db.session.commit()
        place_id = place.id
        unit = Unit(name="rolls")
        db.session.add(unit)
        db.session.commit()
        unit_id = unit.id

    response = client.post(
        "/items/create",
        data={
            "name": "Tape",
            "serial_no": "",
            "description": "Duct tape",
            "qty": "2",
            "cost": "",
            "place_id": str(place_id),
            "unit_id": str(unit_id),
            "sublocation": "",
            "tags": "",
            "date_acquired": "2024-01-15",
        },
    )
    assert response.headers["Location"].endswith("/items")

    with app.app_context():
        item = Item.query.filter_by(name="Tape").one()
        item_id = item.id
        assert item.unit_id == unit_id
        assert item.date_acquired.strftime("%Y-%m-%d") == "2024-01-15"

    details = client.get(f"/items/{item_id}/details")
    assert b"2 rolls" in details.data
    assert b"2024-01-15" in details.data
