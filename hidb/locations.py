from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db

bp = Blueprint('locations', __name__)

@bp.route('/locations')
def index():
    db = get_db()
    locations = db.execute(
        'SELECT l.id, description'
        ' FROM locations l JOIN users u ON l.creator_id = u.id'
        ' ORDER BY l.description ASC'
    ).fetchall()
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
            db = get_db()
            db.execute(
                'INSERT INTO locations (description, creator_id)'
                ' VALUES (?, ?)',
                (description, g.user['id'])
            )
            db.commit()
            return redirect(url_for('locations.index'))

    return render_template('locations/create.html.j2')

def get_locations():
    locations = get_db().execute(
        'SELECT l.id, description FROM locations l ORDER BY description ASC'
    ).fetchall()

    return locations

def get_location(id, check_creator=True):
    location = get_db().execute(
        'SELECT l.id, description, creator_id'
        ' FROM locations l JOIN users u ON l.creator_id = u.id'
        ' WHERE l.id = ?',
        (id,)
    ).fetchone()

    if location is None:
        abort(404, f"Location id {id} doesn't exist.")

    if check_creator and location['creator_id'] != g.user['id']:
        abort(403)

    return location

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
            db = get_db()
            db.execute(
                'UPDATE locations SET description = ?'
                ' WHERE id = ?',
                (description, id)
            )
            db.commit()
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
    db = get_db()
    db.execute('DELETE FROM locations WHERE id = ?', (id,))
    db.commit()
    # forcibly move all items to the first location
    # unless you're deleting it, in which case move them to the second
    loc_to_move_stuff_to = locs[0]['id']
    if loc_to_move_stuff_to == id:
        loc_to_move_stuff_to = locs[1]['id']
    db.execute('UPDATE items SET location = ?', (loc_to_move_stuff_to,))
    db.commit()

    return redirect(url_for('locations.index'))
