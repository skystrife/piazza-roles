from celery import Celery
from .models import *
import os

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
    crawl = Crawl.query.get(crawl_id)
    print("Crawling course: {}".format(crawl.network))
    crawl.finished = True
    db.session.commit()
