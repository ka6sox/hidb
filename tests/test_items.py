from io import BytesIO

from hidb.models import Item, Place, Tag, db


def test_item_sublocation_display_and_search(client, auth, app):
    auth.login()

    with app.app_context():
        garage = Place(name="Garage", creator_id=1)
        cabinet = Place(name="Cabinet 1", parent=garage, creator_id=1)
        shelf = Place(name="Shelf 2", parent=cabinet, creator_id=1)
        db.session.add_all([garage, cabinet, shelf])
        db.session.commit()
        shelf_id = shelf.id

    response = client.post(
        "/items/create",
        data={
            "name": "USB Dongle",
            "serial_no": "",
            "description": "Tiny wireless dongle",
            "qty": "1",
            "cost": "",
            "place_id": str(shelf_id),
            "sublocation": "on top of the dongle",
            "tags": "",
            "photo": (BytesIO(b""), ""),
        },
    )
    assert response.headers["Location"].endswith("/items")

    with app.app_context():
        item = Item.query.filter_by(name="USB Dongle").one()
        item_id = item.id
        assert item.sublocation == "on top of the dongle"

    details = client.get(f"/items/{item_id}/details")
    assert b"Garage / Cabinet 1 / Shelf 2 (on top of the dongle)" in details.data

    results = client.post(
        "/search/run_search",
        data={
            "search_sublocation": "search_sublocation",
            "sublocation": "dongle",
        },
    )
    assert b"Found 1 result" in results.data
    assert b"Garage / Cabinet 1 / Shelf 2 (on top of the dongle)" in results.data


def test_item_tags_display_search_and_update(client, auth, app):
    auth.login()

    with app.app_context():
        bedroom = Place(name="Bedroom", creator_id=1)
        garage = Place(name="Garage", creator_id=1)
        db.session.add_all([bedroom, garage])
        db.session.commit()
        bedroom_id = bedroom.id
        garage_id = garage.id

    first = client.post(
        "/items/create",
        data={
            "name": "Snowboard Boots",
            "serial_no": "",
            "description": "Boots for riding",
            "qty": "1",
            "cost": "",
            "place_id": str(bedroom_id),
            "sublocation": "",
            "tags": "Snowboarding, winter gear, snowboarding",
            "photo": (BytesIO(b""), ""),
        },
    )
    assert first.headers["Location"].endswith("/items")

    second = client.post(
        "/items/create",
        data={
            "name": "Board Wax",
            "serial_no": "",
            "description": "Wax kit",
            "qty": "1",
            "cost": "",
            "place_id": str(garage_id),
            "sublocation": "",
            "tags": "snowboard-maintenance",
            "photo": (BytesIO(b""), ""),
        },
    )
    assert second.headers["Location"].endswith("/items")

    third = client.post(
        "/items/create",
        data={
            "name": "Skis",
            "serial_no": "",
            "description": "Downhill skis",
            "qty": "1",
            "cost": "",
            "place_id": str(garage_id),
            "sublocation": "",
            "tags": "ski",
            "photo": (BytesIO(b""), ""),
        },
    )
    assert third.headers["Location"].endswith("/items")

    with app.app_context():
        boots = Item.query.filter_by(name="Snowboard Boots").one()
        boots_id = boots.id
        assert [t.name for t in boots.tags] == ["snowboarding", "winter gear"]
        assert Tag.query.filter_by(name="snowboarding").one() is not None

    results = client.post(
        "/search/run_search",
        data={
            "search_tags": "search_tags",
            "tags": "snowboard",
        },
    )
    assert b"Found 2 results" in results.data
    assert b"Snowboard Boots" in results.data
    assert b"Board Wax" in results.data
    assert b"Skis" not in results.data
    assert b"snowboard-maintenance" in results.data

    details = client.get(f"/items/{boots_id}/details")
    assert b"snowboarding, winter gear" in details.data

    update = client.post(
        f"/items/{boots_id}/update",
        data={
            "name": "Snowboard Boots",
            "serial_no": "",
            "description": "Boots for riding",
            "qty": "1",
            "cost": "",
            "place_id": str(bedroom_id),
            "sublocation": "",
            "tags": "Powder, boots",
        },
    )
    assert update.headers["Location"].endswith("/items")

    with app.app_context():
        boots = Item.query.get(boots_id)
        assert [t.name for t in boots.tags] == ["boots", "powder"]
