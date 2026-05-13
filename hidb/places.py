from typing import List, Optional, Set

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func, text
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.models import db, Item, Place

bp = Blueprint("places", __name__)


def _places_by_id():
    return {p.id: p for p in Place.query.order_by(Place.id).all()}


def place_path(place_id: int) -> str:
    by_id = _places_by_id()
    parts: List[str] = []
    pid: Optional[int] = place_id
    seen: Set[int] = set()
    while pid is not None and pid in by_id:
        if pid in seen:
            break
        seen.add(pid)
        p = by_id[pid]
        parts.append(p.name)
        pid = p.parent_id
    return " / ".join(reversed(parts))


def place_paths_for_ids(place_ids: list[int]) -> dict[int, str]:
    by_id = _places_by_id()

    def path_for(pid: int) -> str:
        parts: List[str] = []
        cur: Optional[int] = pid
        seen: Set[int] = set()
        while cur is not None and cur in by_id:
            if cur in seen:
                break
            seen.add(cur)
            p = by_id[cur]
            parts.append(p.name)
            cur = p.parent_id
        return " / ".join(reversed(parts))

    return {pid: path_for(pid) for pid in place_ids}


def get_place_options():
    """Sorted list of {id, label} for select widgets."""
    rows = Place.query.order_by(Place.id).all()
    paths = place_paths_for_ids([r.id for r in rows])
    opts = [{"id": r.id, "label": paths[r.id]} for r in rows]
    opts.sort(key=lambda o: o["label"].lower())
    return opts


def get_places_index_rows():
    rows = (
        db.session.query(
            Place.id,
            Place.name,
            Place.description,
            Place.parent_id,
            Place.creator_id,
            func.count(Item.id).label("item_count"),
        )
        .outerjoin(Item, Item.place_id == Place.id)
        .group_by(Place.id)
        .order_by(Place.name.asc())
        .all()
    )
    paths = place_paths_for_ids([r.id for r in rows])
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "parent_id": r.parent_id,
            "creator_id": r.creator_id,
            "item_count": r.item_count,
            "path": paths[r.id],
        }
        for r in rows
    ]


def get_place(place_id: int, check_creator: bool = True):
    row = (
        db.session.query(
            Place.id,
            Place.name,
            Place.description,
            Place.parent_id,
            Place.creator_id,
            func.count(Item.id).label("item_count"),
        )
        .outerjoin(Item, Item.place_id == Place.id)
        .filter(Place.id == place_id)
        .group_by(Place.id)
        .first()
    )
    if row is None:
        abort(404, f"Place id {place_id} doesn't exist.")
    if check_creator and g.user is not None and row.creator_id != g.user.id:
        abort(403)
    path = place_path(row.id)
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "parent_id": row.parent_id,
        "creator_id": row.creator_id,
        "item_count": row.item_count,
        "path": path,
    }


def descendant_place_ids(root_ids: List[int]) -> List[int]:
    """All ids in root_ids plus descendants (SQLite recursive CTE)."""
    if not root_ids:
        return []
    ids = sorted({int(i) for i in root_ids})
    placeholders = ", ".join(str(i) for i in ids)
    sql = f"""
    WITH RECURSIVE tree(id) AS (
      SELECT id FROM places WHERE id IN ({placeholders})
      UNION ALL
      SELECT p.id FROM places AS p INNER JOIN tree ON p.parent_id = tree.id
    )
    SELECT id FROM tree
    """
    result = db.session.execute(text(sql))
    return [r[0] for r in result.fetchall()]


@bp.route("/places")
def index():
    rows = get_places_index_rows()
    return render_template("places/index.html.j2", places=rows)


@bp.route("/places/create", methods=("GET", "POST"))
@login_required
def create():
    parents = get_place_options()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        parent_raw = request.form.get("parent_id", "").strip()
        error = None

        if not name:
            error = "Name is required."

        parent_id = None
        if parent_raw:
            try:
                parent_id = int(parent_raw)
            except ValueError:
                error = "Invalid parent place."

        if error is None and parent_id is not None:
            parent = Place.query.get(parent_id)
            if parent is None:
                error = "Parent place does not exist."
            elif parent.creator_id != g.user.id:
                error = "You cannot add under another user's place."

        if error is not None:
            flash(error)
        else:
            db.session.add(
                Place(
                    name=name,
                    description=description if description else None,
                    parent_id=parent_id,
                    creator_id=g.user.id,
                )
            )
            db.session.commit()
            return redirect(url_for("places.index"))

    return render_template("places/create.html.j2", parents=parents)


@bp.route("/places/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    place = get_place(id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        error = None

        if not name:
            error = "Name is required."

        if error is not None:
            flash(error)
        else:
            place_obj = Place.query.get(id)
            place_obj.name = name
            place_obj.description = description if description else None
            db.session.commit()
            return redirect(url_for("places.index"))

    return render_template("places/update.html.j2", place=place)


@bp.route("/places/<int:id>/delete", methods=("GET", "POST"))
@login_required
def delete(id):
    place = get_place(id)
    place_obj = Place.query.get_or_404(id)

    child_count = Place.query.filter_by(parent_id=id).count()
    item_count = Item.query.filter_by(place_id=id).count()
    blocked = child_count > 0 or item_count > 0

    if request.method == "POST":
        if blocked:
            if child_count > 0:
                flash("Delete or move child places first.")
            else:
                flash("Move or delete items at this place first.")
        else:
            db.session.delete(place_obj)
            db.session.commit()
            return redirect(url_for("places.index"))

    return render_template(
        "places/delete.html.j2",
        place=place,
        blocked=blocked,
        child_count=child_count,
        item_count=item_count,
    )
