import os
import uuid
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
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from hidb.auth import login_required
from hidb.models import db, Item, Place, Tag
from hidb.places import get_place_options, place_path, place_paths_for_ids

bp = Blueprint("items", __name__)


@bp.route("/")
@bp.route("/items")
def index():
    items = get_items()
    places_opts = get_place_options()
    return render_template(
        "items/index.html.j2",
        places=places_opts,
        items=items,
    )


def get_item_count():
    return Item.query.count()


def item_location_path(path, sublocation):
    if sublocation:
        return f"{path} ({sublocation})" if path else sublocation
    return path


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


def get_items(limit=None):
    query = Item.query.order_by(Item.date_added.desc())
    if limit is not None:
        query = query.limit(limit)
    rows = query.all()
    paths = place_paths_for_ids([r.place_id for r in rows])
    return [
        {
            "id": r.id,
            "name": r.name,
            "serial_no": r.serial_no,
            "photo": r.photo,
            "description": r.description,
            "qty": r.qty,
            "cost": r.cost,
            "date_added": r.date_added,
            "sublocation": r.sublocation,
            "tags": sorted(t.name for t in r.tags),
            "tag_list": tag_list(r.tags),
            "place_path": paths.get(r.place_id, ""),
            "location_path": item_location_path(
                paths.get(r.place_id, ""), r.sublocation
            ),
        }
        for r in rows
    ]


def allowed_file_type(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


@bp.route("/items/create", methods=("GET", "POST"))
@login_required
def create():
    places_opts = get_place_options()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        serial_no = request.form.get("serial_no", "").strip()
        description = request.form.get("description", "").strip()
        qty = request.form.get("qty", "").strip()
        cost = request.form.get("cost", "").strip()
        place_raw = request.form.get("place_id", "").strip()
        sublocation = request.form.get("sublocation", "").strip()
        tags_raw = request.form.get("tags", "")

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

        if error is None and place_id is not None:
            if Place.query.get(place_id) is None:
                error = "Place does not exist."

        photo = request.files["photo"]
        filename = ""
        if photo.filename == "":
            filename = ""
        else:
            if not allowed_file_type(photo.filename):
                error = (
                    "Invalid file type. Accepted file types are: "
                    + ", ".join(current_app.config["ALLOWED_EXTENSIONS"])
                )
            else:
                split_tup = os.path.splitext(photo.filename)
                file_extension = split_tup[1][1:]
                filename = secure_filename(str(uuid.uuid4()) + "." + file_extension)
                fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                photo.save(fullpath)

        if error is not None:
            flash(error)
        else:
            item = Item(
                name=name,
                serial_no=serial_no if serial_no else None,
                description=description,
                qty=int(qty),
                cost=float(cost) if cost else None,
                place_id=place_id,
                sublocation=sublocation if sublocation else None,
                photo=filename if filename else None,
                creator_id=g.user.id,
            )
            item.tags = tags_for_input(tags_raw)
            db.session.add(item)
            db.session.commit()
            return redirect(url_for("items.index"))

    return render_template("items/create.html.j2", places=places_opts)


def get_item(id, check_author=True):
    item = Item.query.get(id)

    if item is None:
        abort(404, f"Item id {id} doesn't exist.")

    if check_author and g.user is not None and item.creator_id != g.user.id:
        abort(403)

    path = place_path(item.place_id)
    return {
        "id": item.id,
        "name": item.name,
        "serial_no": item.serial_no,
        "description": item.description,
        "qty": item.qty,
        "cost": item.cost,
        "place_id": item.place_id,
        "sublocation": item.sublocation,
        "tags": sorted(t.name for t in item.tags),
        "tag_list": tag_list(item.tags),
        "place_path": path,
        "location_path": item_location_path(path, item.sublocation),
        "photo": item.photo,
        "date_added": item.date_added,
        "creator_id": item.creator_id,
    }


@bp.route("/items/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    item = get_item(id)
    places_opts = get_place_options()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        serial_no = request.form.get("serial_no", "").strip()
        description = request.form.get("description", "").strip()
        qty = request.form.get("qty", "").strip()
        cost = request.form.get("cost", "").strip()
        place_raw = request.form.get("place_id", "").strip()
        sublocation = request.form.get("sublocation", "").strip()
        tags_raw = request.form.get("tags", "")
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

        if error is None and place_id is not None:
            if Place.query.get(place_id) is None:
                error = "Place does not exist."

        old_filename = None
        new_filename = None
        if "photo" in request.files:
            photo = request.files["photo"]
            if photo.filename != "":
                if not allowed_file_type(photo.filename):
                    error = (
                        "Invalid file type. Accepted file types are: "
                        + ", ".join(current_app.config["ALLOWED_EXTENSIONS"])
                    )
                else:
                    split_tup = os.path.splitext(photo.filename)
                    file_extension = split_tup[1][1:]
                    old_filename = item["photo"]
                    new_filename = secure_filename(
                        str(uuid.uuid4()) + "." + file_extension
                    )
                    fullpath = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], new_filename
                    )
                    photo.save(fullpath)

        if error is not None:
            flash(error)
        else:
            item_obj = Item.query.get(id)
            item_obj.name = name
            item_obj.serial_no = serial_no if serial_no else None
            item_obj.description = description
            item_obj.qty = int(qty)
            item_obj.cost = float(cost) if cost else None
            item_obj.place_id = place_id
            item_obj.sublocation = sublocation if sublocation else None
            item_obj.tags = tags_for_input(tags_raw)

            if new_filename is not None:
                item_obj.photo = new_filename
                if old_filename:
                    old_fullpath = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], old_filename
                    )
                    if os.path.exists(old_fullpath):
                        os.remove(old_fullpath)

            db.session.commit()
            return redirect(url_for("items.index"))

    return render_template(
        "items/update.html.j2", item=item, places=places_opts
    )


@bp.route("/items/<int:id>/details", methods=("GET",))
def details(id):
    item = get_item(id, check_author=False)
    return render_template("items/details.html.j2", item=item)


@bp.route("/items/<int:id>/delete", methods=("GET", "POST"))
@login_required
def delete(id):
    i = get_item(id)
    item_obj = Item.query.get(id)

    if i["photo"]:
        fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], i["photo"])
        if os.path.exists(fullpath):
            os.remove(fullpath)

    db.session.delete(item_obj)
    db.session.commit()
    return redirect(url_for("items.index"))
