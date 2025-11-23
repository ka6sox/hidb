from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.models import db, Item, Location, Room
from .locations import get_locations
from .rooms import get_rooms

bp = Blueprint('search', __name__)

@bp.route('/search')
def index():
  rooms = get_rooms()
  locations = get_locations()
  return render_template('search/index.html.j2', rooms=rooms, locations=locations)

@bp.route('/search/run_search', methods=('POST',))
def run_search():
    if request.method == 'POST':
      do_search_name = request.form.get('search_name')
      do_search_serial_no = request.form.get('search_serial_no')
      do_search_description = request.form.get('search_description')
      do_search_rooms = request.form.get('search_rooms')
      do_search_locations = request.form.get('search_locations')
      do_search_sublocation = request.form.get('search_sublocations')

      # Build query using SQLAlchemy (prevents SQL injection)
      query = db.session.query(
          Item.id,
          Item.name,
          Item.serial_no,
          Item.description,
          Item.qty,
          Item.cost,
          Item.date_added,
          Item.sublocation,
          Item.photo,
          Location.description.label('location')
      ).join(Location, Item.location_id == Location.id)
      
      valid_query = False

      if do_search_name == "search_name":
        search_term = request.form['name']
        query = query.filter(Item.name.like(f'%{search_term}%'))
        valid_query = True
      if do_search_serial_no == "search_serial_no":
        search_term = request.form['serial_no']
        query = query.filter(Item.serial_no.like(f'%{search_term}%'))
        valid_query = True
      if do_search_description == "search_description":
        search_term = request.form['description']
        query = query.filter(Item.description.like(f'%{search_term}%'))
        valid_query = True
      if do_search_rooms == "search_rooms":
        room_ids = [int(r) for r in request.form.getlist('rooms')]
        query = query.filter(Item.room_id.in_(room_ids))
        valid_query = True
      if do_search_locations == "search_locations":
        location_ids = [int(l) for l in request.form.getlist('locations')]
        query = query.filter(Item.location_id.in_(location_ids))
        valid_query = True
      if do_search_sublocation == "search_sublocation":
        search_term = request.form['sublocation']
        query = query.filter(Item.sublocation.like(f'%{search_term}%'))
        valid_query = True

      if valid_query:
        results = query.all()

        if len(results) == 0:
          error = "No matching items were found."
        else:
          error = None
          # Convert to dict-like objects for template compatibility
          results = [{'id': r.id, 'name': r.name, 'serial_no': r.serial_no,
                     'description': r.description, 'qty': r.qty, 'cost': r.cost,
                     'date_added': r.date_added, 'sublocation': r.sublocation,
                     'photo': r.photo, 'location': r.location} for r in results]
      else:
        error = "You must select at least one search criteria."

      if error is not None:
        flash(error)
        return render_template('search/index.html.j2', rooms=get_rooms(), locations=get_locations())
      else:
        return render_template('search/results.html.j2', results=results)
