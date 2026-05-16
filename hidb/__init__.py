import os

from flask import Flask
from .filters import format_currency
from .settings import get_secret_key, get_sqlalchemy_database_uri


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.jinja_env.filters['format_currency'] = format_currency

    db_uri = get_sqlalchemy_database_uri(app.instance_path)
    secret_key = get_secret_key(app.instance_path)
    cookie_secure = os.getenv("SESSION_COOKIE_SECURE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER='hidb/static/photos',
        ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'heif', 'heic'},
        MAX_CONTENT_LENGTH=(16 * 1024 * 1024),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        CSRF_ENABLED=True,
        MIN_PASSWORD_LENGTH=8,
     )

    if test_config is None:
        # load the instance config, if it exists, when not running tests
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    final_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = (
        {'connect_args': {'check_same_thread': False}}
        if str(final_uri).startswith('sqlite')
        else {'pool_pre_ping': True, 'pool_recycle': 280}
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    from . import db
    db.init_app(app)

    from flask_migrate import Migrate
    from .models import db as sqlalchemy_db

    Migrate(app, sqlalchemy_db)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import items
    app.register_blueprint(items.bp)

    from . import places
    app.register_blueprint(places.bp)

    from . import search
    app.register_blueprint(search.bp)

    return app
