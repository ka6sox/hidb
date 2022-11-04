from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db

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
    if request.method == 'POST':
        model_no = request.form['model_no']
        description = request.form['description']
        qty = request.form['qty']
        cost = request.form['cost']
        error = None

        if not model_no:
            error = 'Make/model number is required.'
        if not description:
            error = 'Description is required.'
        if not qty:
            error = 'Quantity is required.'
        if not cost:
            error = 'Cost number is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO items (model_no, description, qty, cost, creator_id)'
                ' VALUES (?, ?, ?, ?, ?)',
                (model_no, description, qty, cost, g.user['id'])
            )
            db.commit()
            return redirect(url_for('items.index'))

    return render_template('items/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('items.index'))

    return render_template('items/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('items.index'))
