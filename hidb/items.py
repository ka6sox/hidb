import os
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from hidb.auth import (
    can_create_item,
    can_delete_item,
    can_edit_item,
    can_use_place_for_item,
    item_owner_id_for,
    login_required,
)
from hidb.models import Item, ItemPhoto, Place, Tag, db
from hidb.places import get_place_options, place_path, place_paths_for_ids
from hidb.units import get_unit_options, parse_unit_id

bp = Blueprint("items", __name__)

MAX_PHOTOS_PER_ITEM = 10


def _items_query():
    return Item.query.options(
        joinedload(Item.photos),
        joinedload(Item.unit),
        joinedload(Item.tags),
    )


@bp.route("/")
@bp.route("/items")
@login_required
def index():
    items = get_items()
    places_opts = get_place_options()
    units_opts = get_unit_options()
    return render_template(
        "items/index.html.j2",
        places=places_opts,
        units=units_opts,
        items=items,
    )


def get_item_count():
    return Item.query.count()


def item_location_path(path, sublocation):
    if sublocation:
        return f"{path} ({sublocation})" if path else sublocation
    return path


def format_qty_display(qty: int, unit_name: str | None) -> str:
    if unit_name:
        return f"{qty} {unit_name}"
    return str(qty)


def parse_tag_names(raw_tags):
    tag_names = []
    seen = set()
    for raw_tag in raw_tags.split(","):
        name = raw_tag.strip().lower()
        if name and name not in seen:
            tag_names.append(name)
            seen.add(name)
    return tag_names


def tag_list(tags):
    return ", ".join(sorted(t.name for t in tags))


def tags_for_input(raw_tags):
    tag_names = parse_tag_names(raw_tags)
    if not tag_names:
        return []

    existing_tags = {
        tag.name: tag for tag in Tag.query.filter(Tag.name.in_(tag_names)).all()
    }
    for name in tag_names:
        if name not in existing_tags:
            existing_tags[name] = Tag(name=name)
            db.session.add(existing_tags[name])
    return [existing_tags[name] for name in tag_names]


def parse_date_acquired(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return datetime.strptime(str(raw).strip(), "%Y-%m-%d")
    except ValueError:
        return None


def sorted_photos(item: Item) -> list[ItemPhoto]:
    return sorted(item.photos, key=lambda p: (p.sort_order, p.id))


def primary_photo_filename(item: Item) -> str | None:
    photos = sorted_photos(item)
    return photos[0].filename if photos else None


def photos_for_dict(item: Item) -> list[dict]:
    return [
        {"id": p.id, "filename": p.filename, "sort_order": p.sort_order}
        for p in sorted_photos(item)
    ]


def item_to_dict(item: Item, path: str) -> dict:
    unit_name = item.unit.name if item.unit else None
    return {
        "id": item.id,
        "name": item.name,
        "serial_no": item.serial_no,
        "photo": primary_photo_filename(item),
        "photos": photos_for_dict(item),
        "description": item.description,
        "qty": item.qty,
        "qty_display": format_qty_display(item.qty, unit_name),
        "unit_id": item.unit_id,
        "unit_name": unit_name,
        "cost": item.cost,
        "date_added": item.date_added,
        "date_acquired": item.date_acquired,
        "creator_id": item.creator_id,
        "place_id": item.place_id,
        "sublocation": item.sublocation,
        "tags": sorted(t.name for t in item.tags),
        "tag_list": tag_list(item.tags),
        "place_path": path,
        "location_path": item_location_path(path, item.sublocation),
    }


def get_items(limit=None):
    query = _items_query().order_by(Item.date_added.desc())
    if limit is not None:
        query = query.limit(limit)
    rows = query.all()
    paths = place_paths_for_ids([r.place_id for r in rows])
    return [item_to_dict(r, paths.get(r.place_id, "")) for r in rows]


def allowed_file_type(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def save_photo_file(file_storage) -> str | None:
    if file_storage is None or file_storage.filename == "":
        return None
    if not allowed_file_type(file_storage.filename):
        return None
    split_tup = os.path.splitext(file_storage.filename)
    file_extension = split_tup[1][1:]
    filename = secure_filename(str(uuid.uuid4()) + "." + file_extension)
    fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(fullpath)
    return filename


def delete_photo_file(filename: str | None) -> None:
    if not filename:
        return
    fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(fullpath):
        os.remove(fullpath)


def add_photos_to_item(item: Item, files) -> str | None:
    """Return error message or None on success."""
    existing = len(item.photos)
    to_add = [f for f in files if f and f.filename]
    if not to_add:
        return None
    if existing + len(to_add) > MAX_PHOTOS_PER_ITEM:
        return f"Each item can have at most {MAX_PHOTOS_PER_ITEM} photos."

    next_order = existing
    if item.photos:
        next_order = max(p.sort_order for p in item.photos) + 1

    for file_storage in to_add:
        if not allowed_file_type(file_storage.filename):
            return (
                "Invalid file type. Accepted file types are: "
                + ", ".join(current_app.config["ALLOWED_EXTENSIONS"])
            )
        filename = save_photo_file(file_storage)
        if filename is None:
            continue
        item.photos.append(
            ItemPhoto(filename=filename, sort_order=next_order)
        )
        next_order += 1
    return None


def delete_item_photo(item: Item, photo_id: int) -> bool:
    photo = next((p for p in item.photos if p.id == photo_id), None)
    if photo is None:
        return False
    delete_photo_file(photo.filename)
    db.session.delete(photo)
    return True


def reorder_item_photos(item: Item, photo_ids: list[int]) -> str | None:
    by_id = {p.id: p for p in item.photos}
    if set(photo_ids) != set(by_id.keys()):
        return "Invalid photo order."
    for order, pid in enumerate(photo_ids):
        by_id[pid].sort_order = order
    return None


def delete_all_item_photos(item: Item) -> None:
    for photo in list(item.photos):
        delete_photo_file(photo.filename)


@bp.route("/items/create", methods=("GET", "POST"))
@login_required
def create():
    if not can_create_item(g.user):
        abort(403)

    places_opts = get_place_options()
    units_opts = get_unit_options()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        serial_no = request.form.get("serial_no", "").strip()
        description = request.form.get("description", "").strip()
        qty = request.form.get("qty", "").strip()
        cost = request.form.get("cost", "").strip()
        place_raw = request.form.get("place_id", "").strip()
        unit_raw = request.form.get("unit_id", "").strip()
        sublocation = request.form.get("sublocation", "").strip()
        tags_raw = request.form.get("tags", "")
        date_acquired_raw = request.form.get("date_acquired", "").strip()

        error = None

        if not name:
            error = "Make/model number is required."
        if not description:
            error = "Description is required."
        if not qty:
            error = "Quantity is required."
        if not place_raw:
            error = "Place is required."

        place_id = None
        if place_raw and error is None:
            try:
                place_id = int(place_raw)
            except ValueError:
                error = "Invalid place."

        unit_id = None
        if error is None and unit_raw:
            unit_id, unit_error = parse_unit_id(unit_raw)
            if unit_error:
                error = unit_error

        if error is None and place_id is not None:
            place = Place.query.get(place_id)
            if place is None:
                error = "Place does not exist."
            elif not can_use_place_for_item(g.user, place):
                error = "You cannot use another user's place."

        photo_error = None
        upload_files = request.files.getlist("photos")
        if error is None and upload_files:
            for f in upload_files:
                if f.filename and not allowed_file_type(f.filename):
                    photo_error = (
                        "Invalid file type. Accepted file types are: "
                        + ", ".join(current_app.config["ALLOWED_EXTENSIONS"])
                    )
                    break

        if error is not None or photo_error is not None:
            flash(error or photo_error)
        else:
            now = datetime.utcnow()
            acquired = parse_date_acquired(date_acquired_raw) or now
            owner_id = item_owner_id_for(g.user)
            item = Item(
                name=name,
                serial_no=serial_no if serial_no else None,
                description=description,
                qty=int(qty),
                cost=float(cost) if cost else None,
                place_id=place_id,
                unit_id=unit_id,
                sublocation=sublocation if sublocation else None,
                creator_id=owner_id,
                date_added=now,
                date_acquired=acquired,
            )
            item.tags = tags_for_input(tags_raw)
            db.session.add(item)
            db.session.flush()

            add_err = add_photos_to_item(item, upload_files)
            if add_err:
                db.session.rollback()
                flash(add_err)
            else:
                db.session.commit()
                return redirect(url_for("items.index"))

    return render_template(
        "items/create.html.j2",
        places=places_opts,
        units=units_opts,
        today=today,
    )


def get_item(id, check_author=True):
    item = _items_query().get(id)

    if item is None:
        abort(404, f"Item id {id} doesn't exist.")

    if check_author and not can_edit_item(g.user, item):
        abort(403)

    path = place_path(item.place_id)
    return item_to_dict(item, path)


@bp.route("/items/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    item_dict = get_item(id)
    places_opts = get_place_options()
    units_opts = get_unit_options()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        serial_no = request.form.get("serial_no", "").strip()
        description = request.form.get("description", "").strip()
        qty = request.form.get("qty", "").strip()
        cost = request.form.get("cost", "").strip()
        place_raw = request.form.get("place_id", "").strip()
        unit_raw = request.form.get("unit_id", "").strip()
        sublocation = request.form.get("sublocation", "").strip()
        tags_raw = request.form.get("tags", "")
        date_acquired_raw = request.form.get("date_acquired", "").strip()
        error = None

        if not name:
            error = "Make/model number is required."
        if not description:
            error = "Description is required."
        if not qty:
            error = "Quantity is required."
        if not place_raw:
            error = "Place is required."

        place_id = None
        if place_raw and error is None:
            try:
                place_id = int(place_raw)
            except ValueError:
                error = "Invalid place."

        unit_id = None
        if error is None and unit_raw:
            unit_id, unit_error = parse_unit_id(unit_raw)
            if unit_error:
                error = unit_error

        if error is None and place_id is not None:
            place = Place.query.get(place_id)
            if place is None:
                error = "Place does not exist."
            elif not can_use_place_for_item(g.user, place):
                error = "You cannot use another user's place."

        acquired = parse_date_acquired(date_acquired_raw)
        if error is None and date_acquired_raw and acquired is None:
            error = "Invalid date acquired."

        upload_files = request.files.getlist("photos")
        if error is None and upload_files:
            for f in upload_files:
                if f.filename and not allowed_file_type(f.filename):
                    error = (
                        "Invalid file type. Accepted file types are: "
                        + ", ".join(current_app.config["ALLOWED_EXTENSIONS"])
                    )
                    break

        if error is not None:
            flash(error)
        else:
            item_obj = _items_query().get(id)
            item_obj.name = name
            item_obj.serial_no = serial_no if serial_no else None
            item_obj.description = description
            item_obj.qty = int(qty)
            item_obj.cost = float(cost) if cost else None
            item_obj.place_id = place_id
            item_obj.unit_id = unit_id
            item_obj.sublocation = sublocation if sublocation else None
            item_obj.tags = tags_for_input(tags_raw)
            if acquired is not None:
                item_obj.date_acquired = acquired

            add_err = add_photos_to_item(item_obj, upload_files)
            if add_err:
                flash(add_err)
            else:
                db.session.commit()
                return redirect(url_for("items.index"))

    acquired_date = item_dict["date_acquired"].strftime("%Y-%m-%d")
    return render_template(
        "items/update.html.j2",
        item=item_dict,
        places=places_opts,
        units=units_opts,
        date_acquired_value=acquired_date,
    )


@bp.route("/items/<int:item_id>/photos/<int:photo_id>/delete", methods=("POST",))
@login_required
def delete_photo(item_id, photo_id):
    item_dict = get_item(item_id)
    item_obj = _items_query().get(item_id)
    if not delete_item_photo(item_obj, photo_id):
        abort(404)
    db.session.commit()
    return redirect(url_for("items.update", id=item_dict["id"]))


@bp.route("/items/<int:item_id>/photos/reorder", methods=("POST",))
@login_required
def reorder_photos(item_id):
    get_item(item_id)
    item_obj = _items_query().get(item_id)
    raw_ids = request.form.getlist("photo_order")
    try:
        photo_ids = [int(x) for x in raw_ids]
    except ValueError:
        flash("Invalid photo order.")
        return redirect(url_for("items.update", id=item_id))

    err = reorder_item_photos(item_obj, photo_ids)
    if err:
        flash(err)
    else:
        db.session.commit()
    return redirect(url_for("items.update", id=item_id))


@bp.route("/items/<int:id>/details", methods=("GET",))
@login_required
def details(id):
    item = get_item(id, check_author=False)
    return render_template("items/details.html.j2", item=item)


@bp.route("/items/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    i = get_item(id, check_author=False)
    if not can_delete_item(g.user, i):
        abort(403)

    item_obj = _items_query().get(id)
    delete_all_item_photos(item_obj)
    db.session.delete(item_obj)
    db.session.commit()
    return redirect(url_for("items.index"))
