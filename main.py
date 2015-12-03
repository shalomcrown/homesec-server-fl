#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, session, redirect, url_for, escape, request, render_template,  g, flash
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
    zones = g.db.query(Zone).filter(Zone.user_id == session['user_id']).all()
    return render_template('show_zones.html', entries=zones)

#============================
@app.route('/add_entry', methods=['POST'])
def add_entry():
    zone = Zone(name=request.form['title'], description=request.form['text'])
    zone.user_id = session['user_id']
    g.db.add(zone)
    g.db.commit()
    return redirect(url_for('show_zones'))

    
#============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = g.db.query(User).filter(User.name.like(request.form['username'])).one()
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
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    #sh.setFormatter(ColoredFormatter())
    logger.addHandler(sh)
    schema_create()
    app.run(host="0.0.0.0", debug=True)
