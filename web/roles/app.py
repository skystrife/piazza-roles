from flask import Flask
from flask_breadcrumbs import Breadcrumbs
from flask_migrate import Migrate

from .controller import bp
from .models import *
from .tasks import *
from .websockets import *


def create_app(use_eventlet=True):
    app = Flask(__name__)

    envvars = [
        'SECRET_KEY', 'FLASK_ENV', 'SQLALCHEMY_DATABASE_URI',
        'SQLALCHEMY_TRACK_MODIFICATIONS', 'CELERY_RESULT_BACKEND',
        'CELERY_BROKER_URL'
    ]
    for envvar in envvars:
        app.config[envvar] = os.getenv(envvar)

    db.init_app(app)
    migrate = Migrate(app, db)
    Breadcrumbs(app)
    configure_celery(app)

    if use_eventlet:
        socketio.init_app(app, **socketio_opts)
    else:
        socketio.init_app(app, async_mode='threading', **socketio_opts)

    app.register_blueprint(bp)

    return app
