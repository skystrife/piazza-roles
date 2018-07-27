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
        backref=db.backref('users', lazy=True))
    crawl = db.relationship('Crawl', backref='network', uselist=False)

    def __init__(self, nid, number, name, term):
        self.nid = nid
        self.number = number
        self.name = name
        self.term = term

    def __repr(self):
        return "<Network: {}:{} ({} {})>".format(self.id, self.nid,
                                                 self.number, self.term)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    networks = db.relationship(
        'Network',
        secondary=network_user,
        lazy='subquery',
        backref=db.backref('networks', lazy=True))

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return "<User: {}>".format(self.email)


class Crawl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(
        db.Integer, db.ForeignKey('network.id'), nullable=False)
    finished = db.Column(db.Boolean, default=False)
    task_id = db.Column(
        db.String(120), index=True)
