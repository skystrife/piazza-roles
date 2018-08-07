from celery import Celery, current_task
from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import functools
import os
import piazza_api
import random
import requests
import time
import traceback

from .models import *
from .utils import *
from .websockets import socketio

celery = Celery(
    __name__,
    backend=os.environ.get('CELERY_RESULT_BACKEND'),
    broker=os.environ.get('CELERY_BROKER_URL'))

logger = get_task_logger(__name__)


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

    piazza = piazza_from_cookie_dict(piazza_jar)
    network = piazza.network(crawl.network.nid)
    feed = network.get_feed(limit=999999, offset=0)

    total_posts = len(feed['feed'])
    for idx, feed_item in enumerate(feed['feed']):
        sleep()
        post = network.get_post(feed_item['id'])
        try:
            crawl.create_actions_from_post(post)
        except Exception as e:
            msg = traceback.format_exc()
            logger.error(msg)
            error = CrawlError(crawl_id=crawl.id, message=msg)
            crawl.errors.append(error)
            db.session.add(error)
        db.session.commit()
        update_progress(idx, total_posts)
    update_progress(total_posts, total_posts, force=True)

    crawl.finished = True
    db.session.commit()


@celery.task(bind=True)
def run_analysis(self, analysis_id):
    analysis = Analysis.query.get(analysis_id)

    @throttle(timedelta(seconds=1))
    def send_progress(progress):
        socketio.emit(
            'progress', progress, namespace='/analysis', room=analysis_id)
        self.update_state(state='PROGRESS', meta=progress)

    def update_sessions_progress(current, total):
        progress = 100 * float(current) / total
        force = (progress >= 100)
        send_progress({'sessions': progress}, force=force)

    analysis.extract_sessions(progress_report=update_sessions_progress)

    log_likelihood = None

    def update_sampler_progress(current_iter,
                                max_iter,
                                current_assignment,
                                max_assignments,
                                ll=None):
        progress = {
            'sessions': 100,
            'sampling': 100 * float(current_iter) / max_iter,
            'iteration': 100 * float(current_assignment) / max_assignments,
            'log_likelihood': ll
        }
        force = (current_iter == max_iter and ll is not None)
        send_progress(progress, force=force)

    analysis.run_sampler(progress_report=update_sampler_progress)
    analysis.finished = True
    db.session.commit()
