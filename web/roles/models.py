from datetime import datetime
from enum import IntEnum, auto
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

network_user = db.Table(
    'network_user',
    db.Column(
        'network_id',
        db.Integer,
        db.ForeignKey('network.id'),
        primary_key=True),
    db.Column(
        'user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True))


class Network(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nid = db.Column(db.String(20), index=True, unique=True, nullable=False)
    number = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    term = db.Column(db.String(120), nullable=False)
    users = db.relationship(
        'User',
        secondary=network_user,
        lazy='subquery',
        backref=db.backref('networks', lazy=True))
    crawl = db.relationship('Crawl', backref='network', uselist=False)

    def __repr(self):
        return "<Network: {}:{} ({} {})>".format(self.id, self.nid,
                                                 self.number, self.term)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User: {}>".format(self.email)


class Crawl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(
        db.Integer, db.ForeignKey('network.id'), nullable=False)
    finished = db.Column(db.Boolean, default=False)
    task_id = db.Column(db.String(120), index=True)
    errors = db.relationship(
        'CrawlError', backref=db.backref('crawl', lazy=True))

    def __repr__(self):
        return "<Crawl: {}>".format(self.id)


class CrawlError(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crawl_id = db.Column(db.Integer, db.ForeignKey('crawl.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return "<CrawlError: {}>".format(self.id)


class ActionType(IntEnum):
    Q_POST_ANON = auto()
    Q_POST_NAME = auto()

    Q_EDIT_MQ_ANON = auto()
    Q_EDIT_OQ_ANON = auto()
    Q_EDIT_MQ_NAME = auto()
    Q_EDIT_OQ_NAME = auto()

    N_POST_ANON = auto()
    N_POST_NAME = auto()

    N_EDIT_MN_ANON = auto()
    N_EDIT_ON_ANON = auto()
    N_EDIT_MN_NAME = auto()
    N_EDIT_ON_NAME = auto()

    SR_POST_MQ_ANON = auto()
    SR_POST_OQ_ANON = auto()
    SR_POST_MQ_NAME = auto()
    SR_POST_OQ_NAME = auto()

    SR_EDIT_MA_MQ_ANON = auto()
    SR_EDIT_MA_OQ_ANON = auto()
    SR_EDIT_OA_MQ_ANON = auto()
    SR_EDIT_OA_OQ_ANON = auto()
    SR_EDIT_MA_MQ_NAME = auto()
    SR_EDIT_MA_OQ_NAME = auto()
    SR_EDIT_OA_MQ_NAME = auto()
    SR_EDIT_OA_OQ_NAME = auto()

    IR_POST = auto()

    IR_EDIT_MA = auto()
    IR_EDIT_OA = auto()

    FOLLOWUP_MQ_ANON = auto()
    FOLLOWUP_OQ_ANON = auto()
    FOLLOWUP_MQ_NAME = auto()
    FOLLOWUP_OQ_NAME = auto()

    FEEDBACK_MF_MQ_ANON = auto()
    FEEDBACK_MF_OQ_ANON = auto()
    FEEDBACK_OF_MQ_ANON = auto()
    FEEDBACK_OF_OQ_ANON = auto()
    FEEDBACK_MF_MQ_NAME = auto()
    FEEDBACK_MF_OQ_NAME = auto()
    FEEDBACK_OF_MQ_NAME = auto()
    FEEDBACK_OF_OQ_NAME = auto()


class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(
        db.Integer, db.ForeignKey('network.id'), nullable=False)
    network = db.relationship(
        'Network', backref=db.backref('actions', lazy=True))
    uid = db.Column(db.String(120), nullable=False, index=True)
    type_id = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    content = db.Column(db.Text, lazy=True)

    def type(self):
        return ActionType(self.type_id)
