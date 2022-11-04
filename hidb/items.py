from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db
from hidb.locations import get_locations

bp = Blueprint('items', __name__)

@bp.route('/')
def index():
    db = get_db()
    items = db.execute(
        'SELECT i.id, model_no, description, qty, date_added'
        ' FROM items i JOIN users u ON i.creator_id = u.id'
        ' ORDER BY date_added DESC'
    ).fetchall()
    return render_template('items/index.html', items=items)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    locations = get_locations()

    if request.method == 'POST':

        model_no = request.form['model_no']
        description = request.form['description']
        qty = request.form['qty']
        cost = request.form['cost']
        location = request.form['location']
        sublocation = request.form['sublocation']
        error = None

        if not model_no:
            error = 'Make/model number is required.'
        if not description:
            error = 'Description is required.'
        if not qty:
            error = 'Quantity is required.'
        if not cost:
            error = 'Cost number is required.'
        if not location:
            error = 'Location is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO items (model_no, description, qty, cost, location, sublocation, creator_id)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                (model_no, description, qty, cost, location, sublocation, g.user['id'])
            )
            db.commit()
            return redirect(url_for('items.index'))

    return render_template('items/create.html', locations=locations)

def get_item(id, check_author=True):
    item = get_db().execute(
        'SELECT i.id, model_no, description, qty, cost, location, sublocation, creator_id'
        ' FROM items i JOIN users u ON i.creator_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if item is None:
        abort(404, f"Item id {id} doesn't exist.")

    if check_author and item['creator_id'] != g.user['id']:
        abort(403)

    return item

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    item = get_item(id)
    locations = get_locations()

    if request.method == 'POST':
        model_no = request.form['model_no']
        description = request.form['description']
        qty = request.form['qty']
        cost = request.form['cost']
        location = request.form['location']
        sublocation = request.form['sublocation']
        error = None

        if not model_no:
            error = 'Make/model number is required.'
        if not description:
            error = 'Description is required.'
        if not qty:
            error = 'Quantity is required.'
        if not cost:
            error = 'Cost number is required.'
        if not location:
            error = 'Location is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE items SET model_no = ?, description = ?, qty = ?, cost = ?, location = ?, sublocation = ?'
                ' WHERE id = ?',
                (model_no, description, qty, cost, location, sublocation, id)
            )
            db.commit()
            return redirect(url_for('items.index'))

    return render_template('items/update.html', item=item, locations=locations)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_item(id)
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('items.index'))
