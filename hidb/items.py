import os
import uuid
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from hidb.auth import login_required
from hidb.db import get_db
from hidb.rooms import get_rooms, get_room
from hidb.locations import get_locations, get_location

bp = Blueprint('items', __name__)

@bp.route('/items')
def index():
    items = get_items()
    rooms = get_rooms()
    locations = get_locations()
    return render_template('items/index.html.j2', rooms=rooms, locations=locations, items=items)

def get_item_count():
  db = get_db()
  num_items = db.execute(
      'SELECT COUNT(id) FROM items'
  ).fetchone()[0]
  return num_items

def get_items(limit = None):
  db = get_db()
  query = 'SELECT i.id, name, serial_no, photo, description, qty, cost, date_added,' \
          '(SELECT description FROM rooms r WHERE room = r.id) as room, ' \
          '(SELECT description FROM locations l WHERE location = l.id) as location, sublocation ' \
          ' FROM items i JOIN users u ON i.creator_id = u.id' \
          ' ORDER BY date_added DESC'
  if limit is not None:
    query += ' LIMIT ' + str(limit)
  items = db.execute(query).fetchall()
  return items

def allowed_file_type(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@bp.route('/items/create', methods=('GET', 'POST'))
@login_required
def create():
    rooms = get_rooms()
    locations = get_locations()

    if request.method == 'POST':

        name = request.form['name']
        serial_no = request.form['serial_no']
        description = request.form['description']
        qty = request.form['qty']
        cost = request.form['cost']
        room = request.form['room']
        location = request.form['location']
        sublocation = request.form['sublocation']

        error = None

        if not name:
            error = 'Make/model number is required.'
        if not description:
            error = 'Description is required.'
        if not qty:
            error = 'Quantity is required.'
        if not cost:
            error = 'Cost number is required.'
        if not room:
            error = 'Room is required.'
        if not location:
            error = 'Location is required.'
        if False and 'photo' not in request.files:
            error = 'No photo was provided.'

        photo = request.files['photo']
        # if user does not select file, browser also
        # submit an empty part without filename
        if photo.filename == '':
            # hack to make photos optional
            filename = ""
            #error = 'No photo was provided.'
        else:
          # blob = photo.read()
          # if len(blob) > current_app.config["MAX_CONTENT_LENGTH"]:
          #     error = 'Photo is too large. Maximum size is ' + current_app.config["MAX_CONTENT_LENGTH"] + '.'
          if not allowed_file_type(photo.filename):
              error = 'Invalid file type. Accepted file types are: ' + ', '.join(current_app.config["ALLOWED_EXTENSIONS"])
          else:
              # ditch whatever filename the file was uploaded as, and create a unique one based on uuid
              # first we yoink the extension
              split_tup = os.path.splitext(photo.filename)
              #print(split_tup)
              # extract the file extension
              #file_name = split_tup[0]
              # first char is a period so we strip it out
              file_extension = split_tup[1][1:]

              # now secure-ize it and make the full path
              filename = secure_filename(str(uuid.uuid4()) + '.' + file_extension)
              fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
              photo.save(fullpath)

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO items (name, serial_no, description, qty, cost, room, location, sublocation, photo, creator_id)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (name, serial_no, description, qty, cost, room, location, sublocation, filename, g.user['id'])
            )
            db.commit()
            return redirect(url_for('items.index'))

    return render_template('items/create.html.j2', rooms=rooms, locations=locations)

def get_item(id, check_author=True):
    item = get_db().execute(
        'SELECT i.id, name, serial_no, description, qty, cost, room, location, sublocation, photo, date_added, creator_id'
        ' FROM items i JOIN users u ON i.creator_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if item is None:
        abort(404, f"Item id {id} doesn't exist.")

    if check_author and g.user is not None and item['creator_id'] != g.user['id']:
        abort(403)

    return item

# BUG: it appears that sometimes when changing an image, the previous image isn't deleted

@bp.route('/items/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    item = get_item(id)
    rooms = get_rooms()
    locations = get_locations()

    if request.method == 'POST':
        name = request.form['name']
        serial_no = request.form['serial_no']
        description = request.form['description']
        qty = request.form['qty']
        cost = request.form['cost']
        room = request.form['room']
        location = request.form['location']
        sublocation = request.form['sublocation']
        error = None

        if not name:
            error = 'Make/model number is required.'
        if not description:
            error = 'Description is required.'
        if not qty:
            error = 'Quantity is required.'
        if not cost:
            error = 'Cost number is required.'
        if not room:
            error = 'Room is required.'
        if not location:
            error = 'Location is required.'

        old_filename = None
        new_filename = None
        if 'photo' in request.files:
          # print("photo in request.files")
          photo = request.files['photo']
          # if user does not select file, browser also
          # submit an empty part without filename
          if photo.filename != '':
            # blob = photo.read()
            # if len(blob) > current_app.config["MAX_CONTENT_LENGTH"]:
            #     error = 'Photo is too large. Maximum size is ' + current_app.config["MAX_CONTENT_LENGTH"] + '.'
            if not allowed_file_type(photo.filename):
              error = 'Invalid file type. Accepted file types are: ' + ', '.join(current_app.config["ALLOWED_EXTENSIONS"])
            else:
              # ditch whatever filename the file was uploaded as, and create a unique one based on uuid
              # first we yoink the extension
              split_tup = os.path.splitext(photo.filename)
              #print(split_tup)
              # extract the file extension
              #file_name = split_tup[0]
              # first char is a period so we strip it out
              file_extension = split_tup[1][1:]

              # now secure-ize it and make the full path
              old_filename = item["photo"]
              new_filename = secure_filename(str(uuid.uuid4()) + '.' + file_extension)
              fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], new_filename)
              photo.save(fullpath)

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE items SET name = ?, serial_no = ?, description = ?, qty = ?, cost = ?, room = ?, location = ?, sublocation = ?'
                ' WHERE id = ?',
                (name, serial_no, description, qty, cost, room, location, sublocation, id)
            )
            db.commit()
            if new_filename is not None:
              db.execute(
                  'UPDATE items SET photo = ?'
                  ' WHERE id = ?',
                  (new_filename, id)
              )
              db.commit()
              # delete the old file
              # print("deleting old file: " + old_filename)
              # print("new file: " + new_filename)
              old_fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], old_filename)
              os.remove(old_fullpath)

            return redirect(url_for('items.index'))

    return render_template('items/update.html.j2', item=item, rooms=rooms, locations=locations)

@bp.route('/items/<int:id>/details', methods=('GET',))
def details(id):
    item = get_item(id)
    room = get_room(item["room"])
    location = get_location(item["location"])
    return render_template('items/details.html.j2', item=item, room=room["description"], location=location["description"])

@bp.route('/items/<int:id>/delete', methods=('GET', 'POST',))
@login_required
def delete(id):
    i = get_item(id)
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ?', (id,))
    db.commit()
    # also delete the photo
    fullpath = os.path.join(current_app.config['UPLOAD_FOLDER'], i['photo'])
    if os.path.exists(fullpath):
        os.remove(fullpath)
    return redirect(url_for('items.index'))
