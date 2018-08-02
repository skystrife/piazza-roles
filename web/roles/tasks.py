from celery import Celery, current_task
from celery.result import AsyncResult
from datetime import datetime, timedelta
import functools
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


class throttle(object):
    def __init__(self, period):
        self.period = period
        self.last_called = datetime.min

    def __call__(self, fun):
        @functools.wraps(fun)
        def wrapper(*args, force=False, **kwargs):
            now = datetime.now()
            elapsed = now - self.last_called

            if elapsed > self.period or force:
                self.last_called = now
                fun(*args, **kwargs)

        return wrapper


@celery.task(bind=True)
def crawl_course(self, crawl_id, piazza_jar):
    CRAWL_DELAY = 0.5

    def sleep():
        sleep_time = CRAWL_DELAY * random.uniform(0.5, 1.5)
        time.sleep(sleep_time)

    @throttle(timedelta(seconds=1))
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
    update_progress(total_posts, total_posts, force=True)

    crawl.finished = True
    db.session.commit()


@celery.task(bind=True)
def construct_sessions(self, analysis_id):
    analysis = Analysis.query.get(analysis_id)

    @throttle(timedelta(seconds=1))
    def update_sessions_progress(current, total):
        progress = 100 * float(current) / total
        socketio.emit(
            'progress', {'sessions': progress},
            namespace='/analysis',
            room=analysis_id)
        self.update_state(state='PROGRESS', meta={'sessions': progress})

    total = Action.query.filter_by(crawl_id=analysis.crawl_id).count()
    current = 0
    for session in analysis.extract_sessions():
        current += len(session.actions)
        update_sessions_progress(current, total)
    update_sessions_progress(current, total, force=True)
