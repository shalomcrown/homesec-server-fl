#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, session, redirect, url_for, jsonify, Response
from flask import escape, request, render_template, g, flash, abort
from flask.views import MethodView
import os
import logging
import  logging.handlers
from db_schema import *
import json
import argparse


#============================
app = Flask(__name__)
app.secret_key = os.urandom(24)
logger = app.logger
is_server = False
server_url = None
FORMAT = '%(asctime)s %(levelname)s %(filename)s %(lineno)s  %(message)s'
logging.basicConfig(format=FORMAT)

#============================
@app.before_request
def before_request():
    g.db = get_session()


#============================
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


#============================
@app.route('/')
def show_zones():
    if not 'user_id' in session:
        return redirect(url_for('login'))
    zones = g.db.query(Zone).filter(Zone.user_id == session['user_id']).all()
    return render_template('show_zones.html', entries=zones)


#============================
@app.route('/add_zone', methods=['POST'])
def add_zone():
    zone = Zone(name=request.form['title'], description=request.form['text'])
    zone.user_id = session['user_id']
    g.db.add(zone)
    g.db.commit()
    return redirect(url_for('show_zones'))


#============================
@app.route('/delete_zone', methods=['POST'])
def delete_zone():
    g.db.query(Zone).filter(Zone.id == request.form['entry_id']).delete()
    g.db.commit()
    return redirect(url_for('show_zones'))


#============================
def remote_login(url, username, password, updateLocalDb = True):
    return None

#============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        query = g.db.query(User).filter(User.name.like(request.form['username']))
        user = query.first()
        if not user and not is_server and request.form['server_url']:
            user = remote_login(request.form['server_url'], request.form['username'], request.form['password'])

        if user:
            password = passwordFromString(request.form['password'])
            if password.upper() == user.password.upper():
                session['username'] = user.name
                session['logged_in'] = True
                session['user_id'] = user.id
                flash('Welcome %s' % user.name)
                return redirect(url_for('show_zones'))
        else:
            flash('Unknown user or bad password')
    if 'username' in session:
        return 'Logged in as %s' % escape(session['username'])
    return render_template('login.html', context={"is_server" : is_server, 'error' : error})


#============================
@app.route('/logout')
def logout():
    session['logged_in'] = False
    if 'username' in session:
        del session['username']
    return redirect(url_for('login'))


#============================
def user_required(f):
    """Checks whether user is logged in or raises error 401."""
    def decorator(*args, **kwargs):
        app.logger.debug('user_required')
        if 'user_id' in session:
            app.logger.debug('User %d in session' % session['user_id'])
            return f(*args, **kwargs)
        else:
            if request.authorization:
                auth = request.authorization
                app.logger.debug('Login auth %s'
                                            % request.authorization.username)
                query = g.db.query(User).filter(User.name.like(auth.username))
                user = query.first()
                if user:
                    app.logger.debug('Login for user %s' % user.name)
                    password = passwordFromString(auth.password)
                    if password.upper() == user.password.upper():
                        session['username'] = user.name
                        session['logged_in'] = True
                        session['user_id'] = user.id
                        app.logger.debug('User %s authenticated' % user)
                        return f(*args, **kwargs)
        app.logger.debug('Return 401')
        return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm="Homesec server"'})
    return decorator


#============================
class ZoneApi (MethodView):
    decorators = [user_required]

    def get(self):
        zones = g.db.query(Zone)\
            .filter(Zone.user_id == session['user_id'])\
            .all()
        return json.dumps([ a.serialize() for a in zones])

#============================
def loadSettings():
     s = get_session()
     server_url = s.query(Settings).filter(Settings.name == 'server_url')

#============================
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    schema_create()

    parser = argparse.ArgumentParser("Homesec server / client")
    parser.add_argument('-s', '--server', action='store_true')
    args = parser.parse_args()
    is_server = args.server

    loadSettings()

    if is_server:
        app.add_url_rule('/api/zones/', endpoint='api_zones',
            view_func=ZoneApi.as_view('api_zones'),
            methods=['GET', 'POST', 'PUT', 'DELETE'])

    app.run(host="0.0.0.0", debug=True,
            port = 5050 if is_server else 8080)
