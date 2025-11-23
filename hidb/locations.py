from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from sqlalchemy import select, func

from hidb.auth import login_required
from hidb.models import db, Location, Item

bp = Blueprint('locations', __name__)

@bp.route('/locations')
def index():
    locations = get_locations()
    return render_template('locations/index.html.j2', locations=locations)

@bp.route('/locations/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        description = request.form['description']
        error = None

        if not description:
            error = 'Description is required.'

        if error is not None:
            flash(error)
        else:
            location = Location(
                description=description,
                creator_id=g.user.id
            )
            db.session.add(location)
            db.session.commit()
            return redirect(url_for('locations.index'))

    return render_template('locations/create.html.j2')

def get_locations():
    # Query locations with item count
    locations = db.session.query(
        Location.id,
        Location.description,
        func.count(Item.id).label('item_count')
    ).outerjoin(Item, Item.location_id == Location.id)\
     .group_by(Location.id)\
     .order_by(Location.description.asc())\
     .all()
    
    # Convert to dict-like objects for template compatibility
    return [{'id': l.id, 'description': l.description, 'item_count': l.item_count} for l in locations]

def get_location(id, check_creator=True):
    location = db.session.query(
        Location.id,
        Location.description,
        Location.creator_id,
        func.count(Item.id).label('item_count')
    ).outerjoin(Item, Item.location_id == Location.id)\
     .filter(Location.id == id)\
     .group_by(Location.id)\
     .first()

    if location is None:
        abort(404, f"Location id {id} doesn't exist.")

    if check_creator and g.user is not None and location.creator_id != g.user.id:
        abort(403)

    return {'id': location.id, 'description': location.description, 'creator_id': location.creator_id, 'item_count': location.item_count}

@bp.route('/locations/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    location = get_location(id)

    if request.method == 'POST':
        description = request.form['description']
        error = None

        if not description:
            error = 'Description is required.'

        if error is not None:
            flash(error)
        else:
            location_obj = Location.query.get(id)
            location_obj.description = description
            db.session.commit()
            return redirect(url_for('locations.index'))

    return render_template('locations/update.html.j2', location=location)

@bp.route('/locations/<int:id>/delete', methods=('GET', 'POST',))
@login_required
def delete(id):
    location = get_location(id)
    locs = get_locations()
    if len(locs) == 1:
        flash('You cannot delete the last location.')
        return render_template('locations/update.html.j2', location=location)
    
    # forcibly move all items to the first location
    # unless you're deleting it, in which case move them to the second
    loc_to_move_stuff_to = locs[0]['id']
    if loc_to_move_stuff_to == id:
        loc_to_move_stuff_to = locs[1]['id']
    
    # Move items to another location
    Item.query.filter_by(location_id=id).update({'location_id': loc_to_move_stuff_to})
    
    # Delete the location
    location_obj = Location.query.get(id)
    db.session.delete(location_obj)
    db.session.commit()

    return redirect(url_for('locations.index'))
