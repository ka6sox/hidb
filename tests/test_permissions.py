from datetime import datetime
from io import BytesIO

from werkzeug.security import generate_password_hash

from hidb.models import db, Item, Place, User


def add_user(username, password, role, editor_for_id=None):
    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role,
        editor_for_id=editor_for_id,
        password_updated_at=datetime.utcnow(),
    )
    db.session.add(user)
    db.session.commit()
    return user


def add_item(name, creator_id, place_id):
    item = Item(
        name=name,
        description=f"{name} description",
        qty=1,
        creator_id=creator_id,
        place_id=place_id,
    )
    db.session.add(item)
    db.session.commit()
    return item


def test_co_owner_cannot_delete_owner_item(client, auth, app):
    with app.app_context():
        place = Place(name="Owner Place", creator_id=1)
        db.session.add(place)
        db.session.commit()
        item = add_item("Owner Item", creator_id=1, place_id=place.id)
        item_id = item.id

    auth.login("other", "other")
    response = client.post(f"/items/{item_id}/delete")

    assert response.status_code == 403
    with app.app_context():
        assert Item.query.get(item_id) is not None


def test_co_owner_can_use_owner_places(client, auth, app):
    with app.app_context():
        owner_place = Place(name="Owner Place", creator_id=1)
        db.session.add(owner_place)
        db.session.commit()
        owner_place_id = owner_place.id

    auth.login("other", "other")

    create_item = client.post(
        "/items/create",
        data={
            "name": "Co-owner Item",
            "serial_no": "",
            "description": "Stored in an owner place",
            "qty": "1",
            "cost": "",
            "place_id": str(owner_place_id),
            "sublocation": "",
            "tags": "",
            "photo": (BytesIO(b""), ""),
        },
    )
    create_child_place = client.post(
        "/places/create",
        data={
            "name": "Co-owner Shelf",
            "description": "",
            "parent_id": str(owner_place_id),
        },
    )

    assert create_item.headers["Location"].endswith("/items")
    assert create_child_place.headers["Location"].endswith("/places")
    with app.app_context():
        item = Item.query.filter_by(name="Co-owner Item").one()
        child_place = Place.query.filter_by(name="Co-owner Shelf").one()
        assert item.creator_id == 2
        assert item.place_id == owner_place_id
        assert child_place.creator_id == 2
        assert child_place.parent_id == owner_place_id


def test_editor_can_edit_only_sponsor_items_and_cannot_delete(client, auth, app):
    with app.app_context():
        editor = add_user("editor", "editorpass", "editor", editor_for_id=1)
        owner_place = Place(name="Owner Place", creator_id=1)
        co_owner_place = Place(name="Co-owner Place", creator_id=2)
        db.session.add_all([owner_place, co_owner_place])
        db.session.commit()
        owner_item = add_item("Owner Item", creator_id=1, place_id=owner_place.id)
        co_owner_item = add_item(
            "Co-owner Item",
            creator_id=2,
            place_id=co_owner_place.id,
        )
        editor_id = editor.id
        owner_item_id = owner_item.id
        co_owner_item_id = co_owner_item.id
        owner_place_id = owner_place.id

    auth.login("editor", "editorpass")
    response = client.post(
        f"/items/{owner_item_id}/update",
        data={
            "name": "Updated Owner Item",
            "serial_no": "",
            "description": "Updated description",
            "qty": "1",
            "cost": "",
            "place_id": str(owner_place_id),
            "sublocation": "",
            "tags": "",
            "photo": (BytesIO(b""), ""),
        },
    )
    assert response.headers["Location"].endswith("/items")

    response = client.post(f"/items/{owner_item_id}/delete")
    assert response.status_code == 403

    response = client.get(f"/items/{co_owner_item_id}/update")
    assert response.status_code == 403

    with app.app_context():
        assert User.query.get(editor_id).editor_for_id == 1
        assert Item.query.get(owner_item_id).name == "Updated Owner Item"
        assert Item.query.get(co_owner_item_id).name == "Co-owner Item"


def test_reader_is_read_only(client, auth, app):
    with app.app_context():
        reader = add_user("reader", "readerpass", "reader")
        place = Place(name="Readable Place", creator_id=1)
        db.session.add(place)
        db.session.commit()
        item = add_item("Readable Item", creator_id=1, place_id=place.id)
        reader_id = reader.id
        item_id = item.id

    auth.login("reader", "readerpass")
    assert client.get(f"/items/{item_id}/details").status_code == 200
    assert client.get("/search").status_code == 200

    create_item = client.post(
        "/items/create",
        data={
            "name": "Reader Item",
            "serial_no": "",
            "description": "Reader description",
            "qty": "1",
            "cost": "",
            "place_id": str(item_id),
            "sublocation": "",
            "tags": "",
            "photo": (BytesIO(b""), ""),
        },
    )
    create_place = client.post(
        "/places/create",
        data={"name": "Reader Place", "description": "", "parent_id": ""},
    )

    assert create_item.status_code == 403
    assert create_place.status_code == 403
    with app.app_context():
        assert User.query.get(reader_id).role == "reader"
        assert Item.query.filter_by(name="Reader Item").first() is None


def test_editor_sees_public_places_from_other_lines(client, auth, app):
    with app.app_context():
        add_user("editor", "editorpass", "editor", editor_for_id=1)
        public_co_place = Place(name="Co-owner Public", creator_id=2, is_private=False)
        private_co_place = Place(
            name="Co-owner Private", creator_id=2, is_private=True
        )
        db.session.add_all([public_co_place, private_co_place])
        db.session.commit()

    auth.login("editor", "editorpass")
    response = client.get("/places")

    assert b"Co-owner Public" in response.data
    assert b"Co-owner Private" not in response.data


def test_co_owner_cannot_see_other_line_private_place(client, auth, app):
    with app.app_context():
        private_owner_place = Place(
            name="Owner Private", creator_id=1, is_private=True
        )
        db.session.add(private_owner_place)
        db.session.commit()

    auth.login("other", "other")
    response = client.get("/places")

    assert b"Owner Private" not in response.data


def test_editor_can_use_sponsor_private_place_for_items(client, auth, app):
    with app.app_context():
        add_user("editor", "editorpass", "editor", editor_for_id=1)
        private_owner_place = Place(
            name="Owner Private Shelf", creator_id=1, is_private=True
        )
        db.session.add(private_owner_place)
        db.session.commit()
        place_id = private_owner_place.id

    auth.login("editor", "editorpass")
    response = client.post(
        "/items/create",
        data={
            "name": "Editor on private shelf",
            "serial_no": "",
            "description": "Allowed for sponsor line",
            "qty": "1",
            "cost": "",
            "place_id": str(place_id),
            "sublocation": "",
            "tags": "",
            "photo": (BytesIO(b""), ""),
        },
    )

    assert response.headers["Location"].endswith("/items")
    with app.app_context():
        item = Item.query.filter_by(name="Editor on private shelf").one()
        assert item.place_id == place_id


def test_only_owner_can_reset_other_passwords(client, auth):
    auth.login("other", "other")
    response = client.post(
        "/auth/users/1/password",
        data={
            "password": "newpassword",
            "confirm_password": "newpassword",
        },
    )

    assert response.status_code == 403
