import os

from flask import Flask
from .filters import format_currency

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.jinja_env.filters['format_currency'] = format_currency

    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'hidb.sqlite'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER='hidb/static/photos',
        ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'heif', 'heic'},
        MAX_CONTENT_LENGTH=(16 * 1024 * 1024)
     )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import items
    app.register_blueprint(items.bp)
    app.add_url_rule('/', endpoint='items.index')
    app.add_url_rule('/items', endpoint='index')

    from . import rooms
    app.register_blueprint(rooms.bp)
    app.add_url_rule('/rooms', endpoint='index')

    from . import locations
    app.register_blueprint(locations.bp)
    app.add_url_rule('/locations', endpoint='index')

    from . import search
    app.register_blueprint(search.bp)
    app.add_url_rule('/search', endpoint='index')

    return app
