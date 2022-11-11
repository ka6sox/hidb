from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db

bp = Blueprint('rooms', __name__)

@bp.route('/rooms')
def index():
  # db = get_db()
  # rooms = db.execute(
  #     'SELECT l.id, description'
  #     ' FROM rooms l JOIN users u ON l.creator_id = u.id'
  #     ' ORDER BY l.description ASC'
  # ).fetchall()
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
            db = get_db()
            db.execute(
                'INSERT INTO rooms (description, creator_id)'
                ' VALUES (?, ?)',
                (description, g.user['id'])
            )
            db.commit()
            return redirect(url_for('rooms.index'))

    return render_template('rooms/create.html.j2')

def get_rooms():
  #print("entering get_rooms")
  # rooms = get_db().execute(
  #     'SELECT l.id, description FROM rooms l ORDER BY description ASC'
  # ).fetchall()
  rooms = get_db().execute(
      'SELECT id, description, '
      '   (SELECT COUNT(*) FROM items WHERE room = r.id) as item_count '
      '   FROM rooms r ORDER BY description ASC'
  ).fetchall()
  #print(str(rooms))
  return rooms

def get_room(id, check_creator=True):
    room = get_db().execute(
        'SELECT r.id, description, creator_id, '
        '(SELECT COUNT(*) FROM items WHERE room = r.id) as item_count '
        ' FROM rooms r JOIN users u ON r.creator_id = u.id'
        ' WHERE r.id = ?',
        (id,)
    ).fetchone()

    if room is None:
        abort(404, f"Room id {id} doesn't exist.")

    if check_creator and g.user is not None and room['creator_id'] != g.user['id']:
        abort(403)

    return room

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
            db = get_db()
            db.execute(
                'UPDATE rooms SET description = ?'
                ' WHERE id = ?',
                (description, id)
            )
            db.commit()
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
    db = get_db()
    db.execute('DELETE FROM rooms WHERE id = ?', (id,))
    db.commit()
    # forcibly move all items to the first room
    # unless you're deleting it, in which case move them to the second
    loc_to_move_stuff_to = locs[0]['id']
    if loc_to_move_stuff_to == id:
        loc_to_move_stuff_to = locs[1]['id']
    db.execute('UPDATE items SET room = ? WHERE room = ?', (loc_to_move_stuff_to, id))
    db.commit()

    return redirect(url_for('rooms.index'))
