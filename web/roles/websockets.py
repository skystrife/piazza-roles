from celery.result import AsyncResult
from flask_socketio import emit, disconnect, join_room, leave_room, SocketIO
from flask import current_app
import functools
import os

from .models import *

socketio = SocketIO()
# HACK: manually initialize the other arguments for the SocketIO server so
# that we can have a delayed init_app() call and a message broker at the
# same time
socketio_opts = {
    'message_queue': os.environ.get('SOCKETIO_MESSAGE_QUEUE'),
    'channel': 'socket-io',
    'logger': True
}

@socketio.on('subscribe', namespace='/network')
def network_subscribe(data):
    network_id = data.get('id')
    if not network_id:
        return False

    net = Network.query.get(network_id)
    join_room(network_id)

    if net.crawl:
        if net.crawl.finished:
            emit('progress', {'progress': 100}, room=network_id)
        else:
            result = AsyncResult(net.crawl.task_id)
            if result.state == 'PROGRESS':
                emit('progress', result.info, room=network_id)

@socketio.on('subscribe', namespace='/analysis')
def analysis_subscribe(data):
    analysis_id = data.get('id')
    if not analysis_id:
        return False

    ana = Analysis.query.get(analysis_id)
    if not ana:
        return False

    join_room(analysis_id)
    emit('progress', ana.progress(), room=analysis_id)
