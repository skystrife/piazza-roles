from celery import Celery, current_task
from celery.result import AsyncResult
from datetime import datetime, timedelta
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


@celery.task(bind=True)
def construct_sessions(self, analysis_id):
    analysis = Analysis.query.get(analysis_id)

    def update_sessions_progress(current, total):
        progress = 100 * float(current) / total
        socketio.emit(
            'progress', {'sessions': progress},
            namespace='/analysis',
            room=analysis_id)
        self.update_state(state='PROGRESS', meta={'sessions': progress})

    actions = Action.query.filter_by(crawl_id=analysis.crawl_id)
    actions = actions.order_by(Action.uid).order_by(Action.time).all()
    total = len(actions)

    gap_len = datetime.timedelta(hours=analysis.session_gap)

    uid = None
    session = None
    prev_action = None
    for idx, action in enumerate(actions):
        update_sessions_progress(idx, total)

        # A session "ends" if either the current user is different (we've
        # moved to a different user's action list) or if the gap length
        # between the previous action and this action is more than the
        # analysis' session_gap
        if action.uid != uid or (prev_action
                                 and action.time - prev_action.time > gap_len):
            if session:
                db.session.add(session)
                db.session.commit()
            session = Session(uid=action.uid, analysis_id=analysis_id)
            uid = action.uid
            prev_action = None

        session.actions.append(action)
        prev_action = action
