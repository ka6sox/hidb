from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db
from .locations import get_locations

bp = Blueprint('search', __name__)

@bp.route('/search')
def index():
  locations = get_locations()
  return render_template('search/index.html', locations=locations)

@bp.route('/search/run_search', methods=('POST',))
def run_search():
    if request.method == 'POST':
      do_search_model_no = request.form.get('search_model_no')
      do_search_description = request.form.get('search_description')
      do_search_locations = request.form.get('search_locations')
      do_search_sublocation = request.form.get('search_sublocations')

      query = 'SELECT i.id, model_no, description, qty, cost, date_added, location, sublocation FROM items i WHERE '

      if do_search_model_no == "search_model_no":
        query += "model_no LIKE '%%%s%%' AND " % request.form['model_no']
      if do_search_description == "search_description":
        query += "description LIKE '%%%s%%' AND " % request.form['description']
      if do_search_locations == "search_locations":
        query += "location IN (" + ",".join(request.form.getlist('locations')) + ") AND "
      if do_search_sublocation == "search_sublocation":
        query += "sublocation LIKE '%%%s%%'" + request.form['sublocation']

      if query.endswith('AND '):
        query = query[:-4]

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

      if error is not None:
        return render_template('search/error.html', error=error, query=query)
      else:
        return render_template('search/results.html', query=query, results=results)
