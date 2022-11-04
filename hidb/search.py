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

      print(request.form)

      do_search_model_no = request.form.get('search_model_no')
      do_search_description = request.form.get('search_description')
      do_search_locations = request.form.get('search_locations')
      do_search_sublocation = request.form.get('search_sublocations')

      what = ""
      if do_search_model_no == "search_model_no":
        what += "model_no: " + request.form['model_no'] + "<br />"
      if do_search_description == "search_description":
        what += "description: " + request.form['description'] + "<br />"
      if do_search_locations == "search_locations":
        what += "locations: "
        locs = request.form.getlist('locations')
        for l in locs:
          what += l + " "
        what += "<br />"
      if do_search_sublocation == "search_sublocation":
        what += "sublocation: " + request.form['sublocation'] + "<br />"

      if len(what) == 0:
        error = "Boogers"
      else:
        error = None

      if error is not None:
        return render_template('search/error.html', error=error)
      else:
        return render_template('search/results.html', results=what)
