from celery import Celery, current_task
from celery.result import AsyncResult
from flask_socketio import SocketIO
import os
import time

from .models import *
from .websockets import socketio_opts

celery = Celery(
    __name__,
    backend=os.environ.get('CELERY_RESULT_BACKEND'),
    broker=os.environ.get('CELERY_BROKER_URL'))


def configure_celery(app):
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask


@celery.task(bind=True)
def crawl_course(self, crawl_id, piazza_jar):
    socketio = SocketIO(**socketio_opts, async_mode='threading')
    crawl = Crawl.query.get(crawl_id)
    print("Crawling course: {}".format(crawl.network))

    for i in range(1, 101):
        print("Progress: {}%".format(i))
        socketio.emit(
            'progress', {'progress': i},
            namespace='/network',
            room=crawl.network_id)
        self.update_state(state='PROGRESS', meta={'progress': i})
        time.sleep(1)

    crawl.finished = True
    db.session.commit()
