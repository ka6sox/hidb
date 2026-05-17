import re

from flask import Blueprint, flash, render_template, request
from sqlalchemy import exists, false, or_, select
from sqlalchemy.orm import joinedload

from hidb.auth import line_owner_labels_for, login_required
from hidb.items import format_qty_display, item_location_path, tag_list
from hidb.models import Item, Tag, item_tags
from hidb.places import (
    descendant_place_ids,
    get_place_options,
    place_ids_matching_path_term,
    place_paths_for_ids,
    visible_place_ids,
)

bp = Blueprint("search", __name__)


def parse_search_terms(q: str) -> list[str]:
    return [t for t in re.split(r"\s+", q.strip()) if t]


def term_filter(term: str, allowed: set[int]):
    pattern = f"%{term}%"
    place_ids = place_ids_matching_path_term(term)
    tag_match = exists(
        select(item_tags.c.item_id)
        .join(Tag, Tag.id == item_tags.c.tag_id)
        .where(
            item_tags.c.item_id == Item.id,
            Tag.name.ilike(pattern),
        )
    )
    clauses = [
        Item.name.ilike(pattern),
        Item.serial_no.ilike(pattern),
        Item.description.ilike(pattern),
        Item.sublocation.ilike(pattern),
        tag_match,
    ]
    if place_ids:
        clauses.append(Item.place_id.in_(place_ids))
    return or_(*clauses)


def resolve_place_filter(raw_ids: list[str], include_subtree: bool) -> tuple[list[int] | None, str | None]:
    if not raw_ids:
        return None, "Select at least one place when filtering by place."
    try:
        place_ids = [int(p) for p in raw_ids]
    except ValueError:
        return None, "Invalid place selection."
    allowed = visible_place_ids()
    place_ids = [pid for pid in place_ids if pid in allowed]
    if not place_ids:
        return None, "You cannot search using places you cannot access."
    if include_subtree:
        place_ids = [pid for pid in descendant_place_ids(place_ids) if pid in allowed]
    return place_ids, None


def build_search_query(terms: list[str], place_ids: list[int] | None):
    allowed = visible_place_ids()
    if not allowed:
        return Item.query.filter(false())

    query = Item.query.filter(Item.place_id.in_(allowed))

    if terms:
        query = query.filter(or_(*[term_filter(term, allowed) for term in terms]))

    if place_ids is not None:
        query = query.filter(Item.place_id.in_(place_ids))

    return query.distinct()

def primary_photo(item: Item) -> str | None:
    if not item.photos:
        return None
    photos = sorted(item.photos, key=lambda p: (p.sort_order, p.id))
    return photos[0].filename if photos else None


def rows_to_results(rows):
    paths = place_paths_for_ids([r.place_id for r in rows])
    owner_labels = line_owner_labels_for(r.creator_id for r in rows)
    results = []
    for r in rows:
        unit_name = r.unit.name if r.unit else None
        results.append(
            {
                "id": r.id,
                "name": r.name,
                "serial_no": r.serial_no,
                "description": r.description,
                "qty": r.qty,
                "qty_display": format_qty_display(r.qty, unit_name),
                "cost": r.cost,
                "date_added": r.date_added,
                "date_acquired": r.date_acquired,
                "creator_id": r.creator_id,
                "photo": primary_photo(r),
                "sublocation": r.sublocation,
                "tags": sorted(t.name for t in r.tags),
                "tag_list": tag_list(r.tags),
                "place_path": paths.get(r.place_id, ""),
                "location_path": item_location_path(
                    paths.get(r.place_id, ""), r.sublocation
                ),
                "line_owner": owner_labels.get(r.creator_id, ""),
            }
        )
    return results


def search_form_context():
    q = request.values.get("q", "")
    selected_places = [int(p) for p in request.values.getlist("places") if p.isdigit()]
    include_subtree = (
        request.values.get("search_place_subtree") == "search_place_subtree"
    )
    return {
        "places": get_place_options(),
        "q": q,
        "selected_places": selected_places,
        "include_subtree": include_subtree,
    }


@bp.route("/search")
@login_required
def index():
    return render_template("search/index.html.j2", **search_form_context())


@bp.route("/search/run_search", methods=("POST",))
@login_required
def run_search():
    from sqlalchemy.orm import joinedload as jl

    q = request.form.get("q", "")
    terms = parse_search_terms(q)
    raw_place_ids = request.form.getlist("places")
    include_subtree = request.form.get("search_place_subtree") == "search_place_subtree"

    ctx = search_form_context()
    ctx["q"] = q
    ctx["selected_places"] = [int(p) for p in raw_place_ids if p.isdigit()]
    ctx["include_subtree"] = include_subtree

    place_ids = None
    if raw_place_ids:
        place_ids, place_error = resolve_place_filter(raw_place_ids, include_subtree)
        if place_error:
            flash(place_error)
            return render_template("search/index.html.j2", **ctx)

    if not terms and place_ids is None:
        flash("Enter a search term or filter by place.")
        return render_template("search/index.html.j2", **ctx)

    query = build_search_query(terms, place_ids).options(
        jl(Item.photos),
        jl(Item.unit),
        jl(Item.tags),
    )
    rows = query.order_by(Item.date_added.desc()).all()

    if len(rows) == 0:
        flash("No matching items were found.")
        return render_template("search/index.html.j2", **ctx)

    return render_template(
        "search/results.html.j2",
        results=rows_to_results(rows),
        q=q,
        selected_places=ctx["selected_places"],
        include_subtree=include_subtree,
    )
