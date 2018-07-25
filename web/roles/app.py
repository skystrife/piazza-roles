from .celery import make_celery
from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from flask_dotenv import DotEnv
from flask_sqlalchemy import SQLAlchemy
import functools
import piazza_api
import requests
import os

app = Flask(__name__)
env = DotEnv(app)
celery = make_celery(app)


@app.before_request
def load_piazza_api():
    email = session.get('email')
    piazza_jar = session.get('piazza_jar')

    if not email or not piazza_jar:
        g.piazza = None
    else:
        piazza_rpc = piazza_api.rpc.PiazzaRPC()
        piazza_rpc.cookies = requests.utils.cookiejar_from_dict(piazza_jar)
        g.piazza = piazza_api.Piazza(piazza_rpc)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.piazza is None:
            flash('You are not logged in.', 'danger')
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


@app.route('/')
def index():
    if g.piazza is not None:
        return redirect(url_for('classes'))
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    session.pop('email', None)
    session.pop('piazza_jar', None)
    piazza_rpc = piazza_api.rpc.PiazzaRPC()
    error = None
    try:
        piazza_rpc.user_login(request.form['email'], request.form['password'])
        session['piazza_jar'] = requests.utils.dict_from_cookiejar(
            piazza_rpc.cookies)
        session['email'] = request.form['email']
        return redirect(url_for('classes'))
    except piazza_api.exceptions.AuthenticationError:
        flash('Email or password incorrect', 'danger')
        return redirect(url_for('index'))
    except:
        flash('Could not communicate with Piazza API', 'danger')
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('piazza_jar', None)
    flash('You were successfully logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/classes')
@login_required
def classes():
    return "TODO"
