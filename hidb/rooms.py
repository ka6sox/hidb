from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from sqlalchemy import select, func

from hidb.auth import login_required
from hidb.models import db, Room, Item

bp = Blueprint('rooms', __name__)

@bp.route('/rooms')
def index():
    rooms = get_rooms()
    return render_template('rooms/index.html.j2', rooms=rooms)

@bp.route('/rooms/create', methods=('GET', 'POST'))
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
            room = Room(
                description=description,
                creator_id=g.user.id
            )
            db.session.add(room)
            db.session.commit()
            return redirect(url_for('rooms.index'))

    return render_template('rooms/create.html.j2')

def get_rooms():
    # Query rooms with item count
    rooms = db.session.query(
        Room.id,
        Room.description,
        func.count(Item.id).label('item_count')
    ).outerjoin(Item, Item.room_id == Room.id)\
     .group_by(Room.id)\
     .order_by(Room.description.asc())\
     .all()
    
    # Convert to dict-like objects for template compatibility
    return [{'id': r.id, 'description': r.description, 'item_count': r.item_count} for r in rooms]

def get_room(id, check_creator=True):
    room = db.session.query(
        Room.id,
        Room.description,
        Room.creator_id,
        func.count(Item.id).label('item_count')
    ).outerjoin(Item, Item.room_id == Room.id)\
     .filter(Room.id == id)\
     .group_by(Room.id)\
     .first()

    if room is None:
        abort(404, f"Room id {id} doesn't exist.")

    if check_creator and g.user is not None and room.creator_id != g.user.id:
        abort(403)

    return {'id': room.id, 'description': room.description, 'creator_id': room.creator_id, 'item_count': room.item_count}

@bp.route('/rooms/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    room = get_room(id)

    if request.method == 'POST':
        description = request.form['description']
        error = None

        if not description:
            error = 'Description is required.'

        if error is not None:
            flash(error)
        else:
            room_obj = Room.query.get(id)
            room_obj.description = description
            db.session.commit()
            return redirect(url_for('rooms.index'))

    return render_template('rooms/update.html.j2', room=room)

@bp.route('/rooms/<int:id>/delete', methods=('GET', 'POST',))
@login_required
def delete(id):
    room = get_room(id)
    locs = get_rooms()
    if len(locs) == 1:
        flash('You cannot delete the last room.')
        return render_template('rooms/update.html.j2', room=room)
    
    # forcibly move all items to the first room
    # unless you're deleting it, in which case move them to the second
    loc_to_move_stuff_to = locs[0]['id']
    if loc_to_move_stuff_to == id:
        loc_to_move_stuff_to = locs[1]['id']
    
    # Move items to another room
    Item.query.filter_by(room_id=id).update({'room_id': loc_to_move_stuff_to})
    
    # Delete the room
    room_obj = Room.query.get(id)
    db.session.delete(room_obj)
    db.session.commit()

    return redirect(url_for('rooms.index'))
