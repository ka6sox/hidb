from flask import Blueprint, flash, redirect, render_template, request, url_for

from hidb.models import db, Item
from hidb.places import descendant_place_ids, get_place_options, place_paths_for_ids

bp = Blueprint("search", __name__)


@bp.route("/search")
def index():
    places_opts = get_place_options()
    return render_template("search/index.html.j2", places=places_opts)


@bp.route("/search/run_search", methods=("POST",))
def run_search():
    do_search_name = request.form.get("search_name")
    do_search_serial_no = request.form.get("search_serial_no")
    do_search_description = request.form.get("search_description")
    do_search_places = request.form.get("search_places")
    include_subtree = request.form.get("search_place_subtree")

    places_opts = get_place_options()

    query = Item.query
    valid_query = False

    if do_search_name == "search_name":
        search_term = request.form["name"]
        query = query.filter(Item.name.like(f"%{search_term}%"))
        valid_query = True
    if do_search_serial_no == "search_serial_no":
        search_term = request.form["serial_no"]
        query = query.filter(Item.serial_no.like(f"%{search_term}%"))
        valid_query = True
    if do_search_description == "search_description":
        search_term = request.form["description"]
        query = query.filter(Item.description.like(f"%{search_term}%"))
        valid_query = True
    if do_search_places == "search_places":
        raw_ids = request.form.getlist("places")
        if not raw_ids:
            flash("Select at least one place when filtering by place.")
            return render_template("search/index.html.j2", places=places_opts)
        place_ids = [int(p) for p in raw_ids]
        if include_subtree == "search_place_subtree":
            place_ids = descendant_place_ids(place_ids)
        query = query.filter(Item.place_id.in_(place_ids))
        valid_query = True

    error = None
    results = None

    if valid_query:
        rows = query.order_by(Item.date_added.desc()).all()
        paths = place_paths_for_ids([r.place_id for r in rows])
        if len(rows) == 0:
            error = "No matching items were found."
        else:
            results = [
                {
                    "id": r.id,
                    "name": r.name,
                    "serial_no": r.serial_no,
                    "description": r.description,
                    "qty": r.qty,
                    "cost": r.cost,
                    "date_added": r.date_added,
                    "photo": r.photo,
                    "place_path": paths.get(r.place_id, ""),
                }
                for r in rows
            ]
    else:
        error = "You must select at least one search criteria."

    if error is not None:
        flash(error)
        return render_template("search/index.html.j2", places=places_opts)

    return render_template("search/results.html.j2", results=results)
