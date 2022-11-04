from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from hidb.auth import login_required
from hidb.db import get_db

bp = Blueprint('search', __name__)

@bp.route('/search')
def index():
    return render_template('search/index.html')

@bp.route('/search/run_search', methods=('GET', 'POST'))
def run_search():
    return render_template('search/results.html')
