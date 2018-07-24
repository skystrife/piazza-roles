from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
import piazza_api
import requests
import os

app = Flask(__name__)

APP_ROOT = os.path.dirname(__file__)
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)
app.secret_key = os.environ.get('SECRET_KEY')

@app.route('/')
def index():
    if 'email' in session and 'piazza_jar' in session:
        return redirect(url_for('classes'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    session.pop('email', None)
    session.pop('piazza_jar', None)
    piazza_rpc = piazza_api.rpc.PiazzaRPC()
    error = None
    try:
        print("trying login")
        print(request.form)
        piazza_rpc.user_login(request.form['email'], request.form['password'])
        session['piazza_jar'] = requests.utils.dict_from_cookiejar(piazza_rpc.cookies)
        session['email'] = request.form['email']
        print("login successful")
        return redirect(url_for('classes'))
    except piazza_api.exceptions.AuthenticationError:
        print("AuthenticationError")
        return render_template('index.html',
                               error='Email or password incorrect')
    except:
        print("Other exception")
        return render_template('index.html',
                               error='Could not communicate with Piazza API')

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('piazza_jar', None)
    return redirect(url_for('index'))

@app.route('/classes')
def classes():
    if not 'email' in session or not 'piazza_jar' in session:
        return redirect(url_for('index'))

    return "TODO"
