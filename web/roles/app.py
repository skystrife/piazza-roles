from flask import (abort, Blueprint, flash, Flask, g, redirect,
                   render_template, request, session, url_for)
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb
from flask_dotenv import DotEnv
from flask_sqlalchemy import SQLAlchemy
import functools
import piazza_api
import requests
from operator import attrgetter

from .models import *
from .tasks import *

app = Flask(__name__)
env = DotEnv(app)
db.init_app(app)
Breadcrumbs(app)
configure_celery(app)


@app.before_request
def load_user():
    uid = session.get('uid')
    piazza_jar = session.get('piazza_jar')

    if not uid or not piazza_jar:
        session.pop('uid', None)
        session.pop('piazza_jar', None)
        g.piazza = None
        g.user = None
    else:
        g.user = User.query.get(uid)
        piazza_rpc = piazza_api.rpc.PiazzaRPC()
        piazza_rpc.cookies = requests.utils.cookiejar_from_dict(piazza_jar)
        g.piazza = piazza_api.Piazza(piazza_rpc)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('You are not logged in.', 'danger')
            return redirect(url_for('.index'))

        return view(*args, **kwargs)

    return wrapped_view


def network_required(view):
    @functools.wraps(view)
    def wrapped_view(network_id, *args, **kwargs):
        g.network = Network.query.get(network_id)
        if g.network is None or not g.network in g.user.networks:
            abort(404)

        return view(*args, network_id=network_id, **kwargs)

    return wrapped_view


@app.route('/')
@register_breadcrumb(app, '.', 'Home')
def index():
    if g.piazza is not None:
        return redirect(url_for('.classes'))
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    session.pop('uid', None)
    session.pop('piazza_jar', None)

    email = request.form['email']
    password = request.form['password']

    piazza_rpc = piazza_api.rpc.PiazzaRPC()
    error = None
    try:
        piazza_rpc.user_login(email, password)
        session['piazza_jar'] = requests.utils.dict_from_cookiejar(
            piazza_rpc.cookies)
        g.piazza = piazza_api.Piazza(piazza_rpc)

        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email)
            db.session.add(user)
            db.session.commit()

        session['uid'] = user.id

        classes = g.piazza.get_user_classes()
        for cls in (cls for cls in classes if cls['is_ta']):
            net = Network.query.filter_by(nid=cls['nid']).first()
            if net is None:
                net = Network(
                    nid=cls['nid'],
                    number=cls['num'],
                    name=cls['name'],
                    term=cls['term'])
                net.users.append(user)
                db.session.add(net)

        db.session.commit()

        return redirect(url_for('.classes'))
    except piazza_api.exceptions.AuthenticationError:
        flash('Email or password incorrect', 'danger')
        session.pop('uid', None)
        session.pop('piazza_jar', None)
        return redirect(url_for('.index'))
    except:
        flash('Could not communicate with Piazza API', 'danger')
        session.pop('uid', None)
        session.pop('piazza_jar', None)
        return redirect(url_for('.index'))


@app.route('/logout')
def logout():
    session.pop('uid', None)
    session.pop('piazza_jar', None)
    flash('You were successfully logged out.', 'success')
    return redirect(url_for('.index'))


@app.route('/classes')
@login_required
@register_breadcrumb(app, '.classes', 'Classes')
def classes():
    def term_to_tuple(term):
        parts = term.split()
        order = ['Other', 'Spring', 'Summer', 'Fall']
        return (parts[1], order.index(parts[0]))

    networks = sorted(g.user.networks, key=attrgetter('number'))
    networks = sorted(
        networks, key=lambda cls: term_to_tuple(cls.term), reverse=True)
    return render_template('classes.html', classes=networks)


def class_name_dlc(*args, **kwargs):
    network_id = request.view_args['network_id']
    net = Network.query.get(network_id)
    if net is None:
        return []
    return [{
        'text': "{} ({})".format(net.number, net.term),
        'url': url_for('.view_class', network_id=network_id)
    }]


@app.route('/class/<network_id>')
@login_required
@network_required
@register_breadcrumb(
    app, '.classes.network_id', '', dynamic_list_constructor=class_name_dlc)
def view_class(network_id):
    return render_template('class.html', network=g.network)
