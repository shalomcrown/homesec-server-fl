#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, session, redirect, url_for, jsonify, Response
from flask import escape, request, render_template, g, flash, abort
from flask.views import MethodView
import os
import logging
import  logging.handlers
from db_schema import *


#============================
app = Flask(__name__)
app.secret_key = os.urandom(24)
logger = logging.getLogger(__name__)


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
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = g.db.query(User) \
            .filter(User.name.like(request.form['username'])) \
            .one()
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
    return render_template('login.html', error=error)


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
                user = g.db.query(User) \
                    .filter(User.name.like(auth.username)) \
                    .one()
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
        return jsonify(zones)

#============================
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    #sh.setFormatter(ColoredFormatter())
    logger.addHandler(sh)
    schema_create()

    app.add_url_rule('/api/zones/', endpoint='api_zones',
        view_func=ZoneApi.as_view('api_zones'),
        methods=['GET', 'POST', 'PUT', 'DELETE'])
    app.run(host="0.0.0.0", debug=True)
