import os
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from hidb.auth import login_required
from hidb.db import get_db
from hidb.locations import get_locations

bp = Blueprint('items', __name__)

@bp.route('/items')
def index():
    db = get_db()
    items = db.execute(
        'SELECT i.id, model_no, description, qty, cost, date_added'
        ' FROM items i JOIN users u ON i.creator_id = u.id'
        ' ORDER BY date_added DESC'
    ).fetchall()
    return render_template('items/index.html', items=items)

def allowed_file_type(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@bp.route('/items/create', methods=('GET', 'POST'))
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
        if 'photo' not in request.files:
            error = 'No photo was provided.'

        photo = request.files['photo']
        # if user does not select file, browser also
        # submit an empty part without filename
        if photo.filename == '':
            error = 'No photo was provided.'

        # blob = photo.read()
        # if len(blob) > current_app.config["MAX_CONTENT_LENGTH"]:
        #     error = 'Photo is too large. Maximum size is ' + current_app.config["MAX_CONTENT_LENGTH"] + '.'
        if not allowed_file_type(photo.filename):
            error = 'Invalid file type. Accepted file types are: ' + ', '.join(current_app.config["ALLOWED_EXTENSIONS"])
        else:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO items (model_no, description, qty, cost, location, sublocation, photo, creator_id)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (model_no, description, qty, cost, location, sublocation, filename, g.user['id'])
            )
            db.commit()
            return redirect(url_for('items.index'))

    return render_template('items/create.html', locations=locations)

def get_item(id, check_author=True):
    item = get_db().execute(
        'SELECT i.id, model_no, description, qty, cost, location, sublocation, photo, date_added, creator_id'
        ' FROM items i JOIN users u ON i.creator_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if item is None:
        abort(404, f"Item id {id} doesn't exist.")

    if check_author and item['creator_id'] != g.user['id']:
        abort(403)

    return item

@bp.route('/items/<int:id>/update', methods=('GET', 'POST'))
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

@bp.route('/items/<int:id>/details', methods=('GET',))
def details(id):
    item = get_item(id)
    return render_template('items/details.html', item=item)

@bp.route('/items/<int:id>/delete', methods=('GET', 'POST',))
@login_required
def delete(id):
    i = get_item(id)
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ?', (id,))
    db.commit()
    fullpath = os.path.join(current_app.config['UPLOAD_FOLDER'], i['photo'])
    if os.path.exists(fullpath):
        os.remove(fullpath)
    return redirect(url_for('items.index'))
