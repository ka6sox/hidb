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

@bp.route('/search/run_search', methods=('GET', 'POST'))
def run_search():
    if request.method == 'POST':
      error = "Boogers"

      if error is not None:
        return render_template('search/error.html', error=error)
      else:
        return render_template('search/results.html', results="boogers")
