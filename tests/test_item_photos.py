from io import BytesIO

from hidb.models import Item, ItemPhoto, Place, db


def _tiny_png():
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_create_item_with_multiple_photos(client, auth, app):
    auth.login()

    with app.app_context():
        place = Place(name="Shelf", creator_id=1)
        db.session.add(place)
        db.session.commit()
        place_id = place.id

    png = _tiny_png()
    response = client.post(
        "/items/create",
        data={
            "name": "Widget",
            "serial_no": "",
            "description": "A widget",
            "qty": "1",
            "cost": "",
            "place_id": str(place_id),
            "sublocation": "",
            "tags": "",
            "date_acquired": "2025-05-01",
            "photos": [
                (BytesIO(png), "a.png"),
                (BytesIO(png), "b.png"),
            ],
        },
    )
    assert response.headers["Location"].endswith("/items")

    with app.app_context():
        item = Item.query.filter_by(name="Widget").one()
        assert len(item.photos) == 2
        cover = sorted(item.photos, key=lambda p: p.sort_order)[0]
        assert cover.sort_order == 0


def test_photo_cap_enforced(client, auth, app):
    auth.login()

    with app.app_context():
        place = Place(name="Bin", creator_id=1)
        db.session.add(place)
        db.session.commit()
        place_id = place.id

    png = _tiny_png()
    files = [(BytesIO(png), f"p{i}.png") for i in range(11)]
    response = client.post(
        "/items/create",
        data={
            "name": "Overloaded",
            "serial_no": "",
            "description": "Too many photos",
            "qty": "1",
            "cost": "",
            "place_id": str(place_id),
            "sublocation": "",
            "tags": "",
            "photos": files,
        },
    )
    assert response.status_code == 200
    assert b"at most 10 photos" in response.data

    with app.app_context():
        assert Item.query.filter_by(name="Overloaded").first() is None


def test_delete_photo(client, auth, app):
    auth.login()
    png = _tiny_png()

    with app.app_context():
        place = Place(name="Closet", creator_id=1)
        db.session.add(place)
        db.session.flush()
        item = Item(
            name="Lamp",
            description="Desk lamp",
            qty=1,
            place_id=place.id,
            creator_id=1,
        )
        db.session.add(item)
        db.session.flush()
        p1 = ItemPhoto(item_id=item.id, filename="one.png", sort_order=0)
        p2 = ItemPhoto(item_id=item.id, filename="two.png", sort_order=1)
        db.session.add_all([p1, p2])
        db.session.commit()
        item_id = item.id
        photo_id = p1.id

    response = client.post(f"/items/{item_id}/photos/{photo_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        item = Item.query.get(item_id)
        assert len(item.photos) == 1
        assert item.photos[0].filename == "two.png"
