import os
import uuid
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from sqlalchemy import select

from hidb.auth import login_required
from hidb.models import db, Item, Room, Location
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
    return Item.query.count()

def get_items(limit=None):
    query = db.session.query(
        Item.id,
        Item.name,
        Item.serial_no,
        Item.photo,
        Item.description,
        Item.qty,
        Item.cost,
        Item.date_added,
        Room.description.label('room'),
        Location.description.label('location'),
        Item.sublocation
    ).join(Room, Item.room_id == Room.id)\
     .join(Location, Item.location_id == Location.id)\
     .order_by(Item.date_added.desc())
    
    if limit is not None:
        query = query.limit(limit)
    
    items = query.all()
    
    # Convert to dict-like objects for template compatibility
    return [{'id': i.id, 'name': i.name, 'serial_no': i.serial_no, 'photo': i.photo, 
             'description': i.description, 'qty': i.qty, 'cost': i.cost, 
             'date_added': i.date_added, 'room': i.room, 'location': i.location, 
             'sublocation': i.sublocation} for i in items]

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
            item = Item(
                name=name,
                serial_no=serial_no if serial_no else None,
                description=description,
                qty=int(qty),
                cost=float(cost) if cost else None,
                room_id=int(room),
                location_id=int(location),
                sublocation=sublocation if sublocation else None,
                photo=filename if filename else None,
                creator_id=g.user.id
            )
            db.session.add(item)
            db.session.commit()
            return redirect(url_for('items.index'))

    return render_template('items/create.html.j2', rooms=rooms, locations=locations)

def get_item(id, check_author=True):
    item = Item.query.get(id)

    if item is None:
        abort(404, f"Item id {id} doesn't exist.")

    if check_author and g.user is not None and item.creator_id != g.user.id:
        abort(403)

    # Return dict-like object for template compatibility
    return {
        'id': item.id,
        'name': item.name,
        'serial_no': item.serial_no,
        'description': item.description,
        'qty': item.qty,
        'cost': item.cost,
        'room': item.room_id,
        'location': item.location_id,
        'sublocation': item.sublocation,
        'photo': item.photo,
        'date_added': item.date_added,
        'creator_id': item.creator_id
    }

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
            item_obj = Item.query.get(id)
            item_obj.name = name
            item_obj.serial_no = serial_no if serial_no else None
            item_obj.description = description
            item_obj.qty = int(qty)
            item_obj.cost = float(cost) if cost else None
            item_obj.room_id = int(room)
            item_obj.location_id = int(location)
            item_obj.sublocation = sublocation if sublocation else None
            
            if new_filename is not None:
                item_obj.photo = new_filename
                # delete the old file (if one exists)
                # print("deleting old file: " + old_filename)
                # print("new file: " + new_filename)
                if old_filename is not None and len(old_filename) > 0:
                    old_fullpath = os.path.join(current_app.config["UPLOAD_FOLDER"], old_filename)
                    os.remove(old_fullpath)
            
            db.session.commit()
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
    item_obj = Item.query.get(id)
    
    # also delete the photo
    if i['photo']:
        fullpath = os.path.join(current_app.config['UPLOAD_FOLDER'], i['photo'])
        if os.path.exists(fullpath):
            os.remove(fullpath)
    
    db.session.delete(item_obj)
    db.session.commit()
    return redirect(url_for('items.index'))
