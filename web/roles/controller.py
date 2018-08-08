from flask import (current_app, abort, Blueprint, flash, Flask, g, redirect,
                   render_template, request, session, url_for)
from flask_breadcrumbs import (Breadcrumbs, default_breadcrumb_root,
                               register_breadcrumb)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import functools
from operator import attrgetter
import piazza_api
import requests
from sqlalchemy import distinct, func

from .forms import *
from .models import *
from .tasks import *
from .utils import *

bp = Blueprint('main', __name__)
default_breadcrumb_root(bp, '.')


@bp.before_app_request
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
        g.piazza = piazza_from_cookie_dict(piazza_jar)


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


def analysis_required(view):
    @functools.wraps(view)
    def wrapped_view(analysis_id, *args, **kwargs):
        g.analysis = Analysis.query.get(analysis_id)
        if g.analysis is None or not g.analysis.crawl.network == g.network:
            abort(404)

        return view(*args, analysis_id=analysis_id, **kwargs)

    return wrapped_view


@bp.route('/')
@register_breadcrumb(bp, '.', 'Home')
def index():
    if g.user and g.piazza:
        return redirect(url_for('.classes'))
    return render_template('index.html')


@bp.route('/login', methods=['POST'])
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
            piazza_rpc.session.cookies)
        g.piazza = piazza_api.Piazza(piazza_rpc)

        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email)
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


@bp.route('/logout')
def logout():
    session.pop('uid', None)
    session.pop('piazza_jar', None)
    flash('You were successfully logged out.', 'success')
    return redirect(url_for('.index'))


@bp.route('/classes')
@login_required
@register_breadcrumb(bp, '.classes', 'Classes')
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


@bp.route('/class/<network_id>')
@login_required
@network_required
@register_breadcrumb(
    bp, '.classes.network_id', '', dynamic_list_constructor=class_name_dlc)
def view_class(network_id):
    return render_template('class.html', network=g.network)


@bp.route('/class/<network_id>/crawl', methods=['GET'])
@login_required
@network_required
@register_breadcrumb(bp, '.classes.network_id.crawl', 'Crawl')
def crawl_class(network_id):
    return render_template('crawl.html', network=g.network)


@bp.route('/class/<network_id>/crawl', methods=['POST'])
@login_required
@network_required
@register_breadcrumb(bp, '.classes.network_id.crawl', 'Crawl')
def start_crawl_class(network_id):
    try:
        email = request.form['email']
        password = request.form['password']

        piazza_rpc = piazza_api.rpc.PiazzaRPC()
        piazza_rpc.user_login(email, password)
        piazza = piazza_api.Piazza(piazza_rpc)
        net = piazza.network(g.network.nid)
        net.get_feed(limit=1)
    except:
        flash('Could not communicate with Piazza. Try again?', 'danger')
        return render_template('crawl.html', network=g.network)

    if g.network.crawl:
        db.session.delete(g.network.crawl)
        db.session.commit()

    crawl = Crawl(network=g.network)
    db.session.add(crawl)
    db.session.commit()

    cookiejar = requests.utils.dict_from_cookiejar(piazza_rpc.session.cookies)
    task = crawl_course.delay(crawl.id, cookiejar)
    crawl.task_id = task.id
    db.session.commit()

    return render_template('crawl.html', network=g.network)


@bp.route('/class/<network_id>/analysis', methods=['GET', 'POST'])
@login_required
@network_required
@register_breadcrumb(bp, '.classes.network_id.analyze', 'Analysis')
def new_analysis(network_id):
    form = AnalysisForm()
    if form.validate_on_submit():
        analysis = Analysis(
            crawl_id=g.network.crawl.id,
            session_gap=form.session_gap.data,
            role_count=form.role_count.data,
            max_iterations=form.max_iterations.data,
            proportion_smoothing=form.proportion_smoothing.data,
            role_smoothing=form.role_smoothing.data)
        db.session.add(analysis)
        db.session.commit()

        task = run_analysis.delay(analysis.id)
        analysis.task_id = task.id
        db.session.commit()

        return redirect(
            url_for(
                '.analysis', network_id=network_id, analysis_id=analysis.id))
    return render_template('new_analysis.html', network=g.network, form=form)


@bp.route('/class/<network_id>/analysis/<analysis_id>')
@login_required
@network_required
@analysis_required
@register_breadcrumb(bp, '.classes.network_id.analyze.analysis_id',
                     'View analysis')
def analysis(network_id, analysis_id):
    view = {
        'network': g.network,
        'analysis': g.analysis,
        'progress': g.analysis.progress(),
        'total_users': g.network.crawl.total_users()
    }

    view['action_type_map'] = {
        int(atype): {
            'name': atype.name,
            'description': atype.description()
        }
        for atype in ActionType
    }

    view['role_json'] = None
    if g.analysis.finished:
        view['role_json'] = {
            role.id: [aw.weight for aw in role.weights]
            for role in g.analysis.roles
        }

    session_stats = []
    session_stats.append(('Total actions', len(g.network.crawl.actions)))
    session_stats.append(('Total sessions', len(g.analysis.sessions)))
    session_stats.append(('Total users', g.network.crawl.total_users()))

    length_stats = g.analysis.session_length_stats()
    session_stats.append(('Average session length (actions)',
                          length_stats.avg))
    session_stats.append(('Standard deviation (actions)', length_stats.std))

    view['session_stats'] = session_stats

    return render_template('analysis.html', **view)


def role_number_dlc(*args, **kwargs):
    role_num = request.view_args['role_num']
    return [{
        'text': "Role {}".format(role_num),
        'url': url_for('.role', **request.view_args)
    }]


@bp.route('/class/<network_id>/analysis/<analysis_id>/role/<int:role_num>')
@login_required
@network_required
@analysis_required
@register_breadcrumb(
    bp,
    '.classes.network_id.analyze.analysis_id.role_num',
    '',
    dynamic_list_constructor=role_number_dlc)
def role(network_id, analysis_id, role_num):
    try:
        role = g.analysis.roles[role_num - 1]
    except:
        abort(404)

    # This is a bit of a crazy query, but the goal is to get everything
    # into one list of tuples we can iterate for the user list in the view
    #
    # We're grabbing all of the role proportions for this role, then
    # joining the sessions on the user id, using aggregation to count the
    # number of sessions, and then getting back tuples of the form
    # (uid, weight, session_count)

    session_count = func.count(Session.id)
    proportions = db.session.query(RoleProportion.uid,
                                   RoleProportion.weight,
                                   session_count.label('session_count'))\
                            .filter(RoleProportion.uid == Session.uid)\
                            .filter(RoleProportion.role_id == Session.role_id)\
                            .filter(RoleProportion.role_id == role.id)\
                            .group_by(RoleProportion.uid,
                                      RoleProportion.weight)\
                            .order_by(RoleProportion.weight.desc())\
                            .all()

    sessions = db.session.query(Session, RoleProportion)\
            .filter(Session.analysis_id == analysis_id)\
            .filter(Session.role_id == role.id)\
            .filter(Session.uid == RoleProportion.uid)\
            .filter(Session.role_id == RoleProportion.role_id)\
            .order_by(RoleProportion.weight.desc())\
            .order_by(Session.uid)\
            .order_by(Session.id)\
            .all()

    role_json = [aw.weight for aw in role.weights]

    action_type_map = {
        int(atype): {
            'name': atype.name,
            'description': atype.description()
        }
        for atype in ActionType
    }

    return render_template(
        'role.html',
        network=g.network,
        analysis=g.analysis,
        role=role,
        role_num=role_num,
        proportions=proportions,
        sessions=sessions,
        role_json=role_json,
        action_type_map=action_type_map,
        ActionType=ActionType)


def uid_dlc(*args, **kwargs):
    uid = request.view_args['uid']
    return [{
        'text': "User {}".format(uid),
        'url': url_for('.user', **request.view_args)
    }]


@bp.route('/class/<network_id>/analysis/<analysis_id>/user/<uid>')
@login_required
@network_required
@analysis_required
@register_breadcrumb(
    bp,
    '.classes.network_id.analyze.analysis_id.user',
    '',
    dynamic_list_constructor=uid_dlc)
def user(network_id, analysis_id, uid):
    proportions = RoleProportion.query.filter_by(analysis=g.analysis)\
            .filter_by(uid=uid)\
            .order_by(RoleProportion.role_id)
    proportions = [prop.weight for prop in proportions]

    sessions = Session.query.filter_by(analysis=g.analysis)\
            .filter_by(uid=uid)\
            .all()

    role_number = {
        role.id: g.analysis.roles.index(role) + 1
        for role in g.analysis.roles
    }

    if not proportions:
        abort(404)

    return render_template(
        'user.html',
        network=g.network,
        analysis=g.analysis,
        uid=uid,
        proportions=proportions,
        sessions=sessions,
        role_number=role_number,
        ActionType=ActionType)
