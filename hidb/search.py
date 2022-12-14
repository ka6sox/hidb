from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db
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

      query = 'SELECT i.id, name, serial_no, description, qty, cost, date_added, sublocation, photo, (SELECT description FROM locations l WHERE location = l.id) as location FROM items i WHERE '
      valid_query = False

      if do_search_name == "search_name":
        query += "name LIKE '%%%s%%' AND " % request.form['name']
        valid_query = True
      if do_search_serial_no == "search_serial_no":
        query += "serial_no LIKE '%%%s%%' AND " % request.form['serial_no']
        valid_query = True
      if do_search_description == "search_description":
        query += "description LIKE '%%%s%%' AND " % request.form['description']
        valid_query = True
      if do_search_rooms == "search_rooms":
        query += "room IN (" + ",".join(request.form.getlist('rooms')) + ") AND "
        valid_query = True
      if do_search_locations == "search_locations":
        query += "location IN (" + ",".join(request.form.getlist('locations')) + ") AND "
        valid_query = True
      if do_search_sublocation == "search_sublocation":
        query += "sublocation LIKE '%%%s%%'" + request.form['sublocation']
        valid_query = True

      if query.endswith('AND '):
        query = query[:-4]

      if valid_query:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(query)
        db.commit()
        results = cursor.fetchall()

        # print(len(results))
        # print(results)

        if len(results) == 0:
          error = "No matching items were found."
        else:
          error = None
      else:
        error = "You must select at least one search criteria."

      print("DEBUG: query = %s" % query)

      if error is not None:
        flash(error)
        return render_template('search/index.html.j2', rooms=get_rooms(), locations=get_locations())
      else:
        return render_template('search/results.html.j2', results=results)
