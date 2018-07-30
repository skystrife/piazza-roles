from celery import Celery, current_task
from celery.result import AsyncResult
import os
import piazza_api
import random
import requests
import time

from .models import *
from .websockets import socketio

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
    CRAWL_DELAY = 0.5
    def sleep():
        sleep_time = CRAWL_DELAY * random.uniform(0.5, 1.5)
        time.sleep(sleep_time)

    def update_progress(current, total):
        progress = 100 * float(current) / total
        socketio.emit(
            'progress', {'progress': progress},
            namespace='/network',
            room=crawl.network_id)
        self.update_state(state='PROGRESS', meta={'progress': progress})


    crawl = Crawl.query.get(crawl_id)
    print("Crawling {}".format(crawl.network))

    piazza_rpc = piazza_api.rpc.PiazzaRPC()
    piazza_rpc.cookies = requests.utils.cookiejar_from_dict(piazza_jar)
    piazza = piazza_api.Piazza(piazza_rpc)
    network = piazza.network(crawl.network.nid)
    feed = network.get_feed(limit=999999, offset=0)

    total_posts = len(feed['feed'])
    for idx, feed_item in enumerate(feed['feed']):
        sleep()
        post = network.get_post(feed_item['id'])
        print(post)
        crawl.create_actions_from_post(post)
        db.session.commit()
        update_progress(idx, total_posts)

    crawl.finished = True
    db.session.commit()
