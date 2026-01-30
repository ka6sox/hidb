from . import create_app
from .settings import config
from .models import db

application = create_app()

# Initialize database tables if they don't exist
with application.app_context():
    db.create_all()

if config.ENVIRONMENT == "development":
    application.run(host=config.HOST, port=config.PORT, debug=True)
