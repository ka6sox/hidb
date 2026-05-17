from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import abort

from hidb.auth import can_create_item, login_required
from hidb.models import Unit, db

bp = Blueprint("units", __name__)


def normalize_unit_name(name: str) -> str:
    return name.strip().lower()


def get_unit_options():
    rows = Unit.query.order_by(Unit.name).all()
    return [{"id": u.id, "label": u.name} for u in rows]


def get_or_create_unit(name: str) -> Unit | None:
    normalized = normalize_unit_name(name)
    if not normalized:
        return None
    existing = Unit.query.filter_by(name=normalized).first()
    if existing is not None:
        return existing
    unit = Unit(name=normalized)
    db.session.add(unit)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return Unit.query.filter_by(name=normalized).one()
    return unit


def parse_unit_id(raw: str) -> tuple[int | None, str | None]:
    if not raw or not raw.strip():
        return None, None
    try:
        return int(raw.strip()), None
    except ValueError:
        return None, "Invalid unit."


def _wants_embed_response():
    return (
        request.args.get("embed") == "1"
        or request.form.get("embed") == "1"
        or "application/json" in request.headers.get("Accept", "")
    )


@bp.route("/units/create", methods=("GET", "POST"))
@login_required
def create():
    if not can_create_item(g.user):
        abort(403)

    embed = request.args.get("embed") == "1" or request.form.get("embed") == "1"

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        error = None
        if not name:
            error = "Unit name is required."

        if error is not None:
            if _wants_embed_response():
                html = render_template(
                    "units/_form.html.j2",
                    embed=True,
                    error=error,
                )
                return jsonify({"ok": False, "html": html}), 400
            flash(error)
        else:
            unit = get_or_create_unit(name)
            if unit is None:
                if _wants_embed_response():
                    html = render_template(
                        "units/_form.html.j2",
                        embed=True,
                        error="Unit name is required.",
                    )
                    return jsonify({"ok": False, "html": html}), 400
                flash("Unit name is required.")
            else:
                db.session.commit()
                if _wants_embed_response():
                    return jsonify({"ok": True, "id": unit.id, "label": unit.name})
                return redirect(url_for("items.index"))

    if embed:
        return render_template("units/_form.html.j2", embed=True, error=None)

    return redirect(url_for("items.index"))
