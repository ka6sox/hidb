from io import BytesIO

from hidb.models import Item, Place, db


def _create_item(client, *, name, place_id, sublocation="", tags="", description="Item description"):
    return client.post(
        "/items/create",
        data={
            "name": name,
            "serial_no": "",
            "description": description,
            "qty": "1",
            "cost": "",
            "place_id": str(place_id),
            "sublocation": sublocation,
            "tags": tags,
            "photo": (BytesIO(b""), ""),
        },
    )


def test_search_or_terms_match_any_field(client, auth, app):
    auth.login()

    with app.app_context():
        bedroom = Place(name="Bedroom", creator_id=1)
        garage = Place(name="Garage", creator_id=1)
        db.session.add_all([bedroom, garage])
        db.session.commit()
        bedroom_id = bedroom.id
        garage_id = garage.id

    _create_item(
        client,
        name="Snowboard Boots",
        place_id=bedroom_id,
        tags="snowboarding, winter gear",
    )
    _create_item(
        client,
        name="Board Wax",
        place_id=garage_id,
        tags="snowboard-maintenance",
    )
    _create_item(client, name="Skis", place_id=garage_id, tags="ski")

    results = client.post("/search/run_search", data={"q": "snowboard garage"})
    assert b"3 match" in results.data
    assert b"test (Owner)" in results.data
    assert b"Snowboard Boots" in results.data
    assert b"Board Wax" in results.data
    assert b"Skis" in results.data


def test_search_matches_sublocation_and_place_path(client, auth, app):
    auth.login()

    with app.app_context():
        garage = Place(name="Garage", creator_id=1)
        cabinet = Place(name="Cabinet 1", parent=garage, creator_id=1)
        shelf = Place(name="Shelf 2", parent=cabinet, creator_id=1)
        db.session.add_all([garage, cabinet, shelf])
        db.session.commit()
        shelf_id = shelf.id

    _create_item(
        client,
        name="USB Dongle",
        place_id=shelf_id,
        sublocation="on top of the dongle",
        description="Tiny wireless dongle",
    )

    by_sublocation = client.post("/search/run_search", data={"q": "dongle"})
    assert b"Search results" in by_sublocation.data
    assert b"USB Dongle" in by_sublocation.data

    by_place = client.post("/search/run_search", data={"q": "Garage"})
    assert b"USB Dongle" in by_place.data


def test_search_place_filter_only(client, auth, app):
    auth.login()

    with app.app_context():
        bedroom = Place(name="Bedroom", creator_id=1)
        garage = Place(name="Garage", creator_id=1)
        db.session.add_all([bedroom, garage])
        db.session.commit()
        bedroom_id = bedroom.id
        garage_id = garage.id

    _create_item(client, name="Bedroom Lamp", place_id=bedroom_id)
    _create_item(client, name="Garage Tool", place_id=garage_id)

    results = client.post(
        "/search/run_search",
        data={"places": [str(bedroom_id)]},
    )
    assert b"1 match" in results.data
    assert b"Bedroom Lamp" in results.data
    assert b"Garage Tool" not in results.data


def test_search_combined_text_and_place(client, auth, app):
    auth.login()

    with app.app_context():
        bedroom = Place(name="Bedroom", creator_id=1)
        garage = Place(name="Garage", creator_id=1)
        db.session.add_all([bedroom, garage])
        db.session.commit()
        bedroom_id = bedroom.id
        garage_id = garage.id

    _create_item(client, name="Snowboard Boots", place_id=bedroom_id, tags="snowboard")
    _create_item(client, name="Board Wax", place_id=garage_id, tags="snowboard")

    results = client.post(
        "/search/run_search",
        data={"q": "snowboard", "places": [str(bedroom_id)]},
    )
    assert b"1 match" in results.data
    assert b"Snowboard Boots" in results.data
    assert b"Board Wax" not in results.data


def test_search_requires_criteria(client, auth):
    auth.login()
    response = client.post("/search/run_search", data={})
    assert b"Enter a search term or filter by place." in response.data
