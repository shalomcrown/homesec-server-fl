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
    #cur = g.db.execute('select title, text from entries order by id desc')
    #entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    return render_template('show_zones.html', entries=[{}])

#============================
@app.route('/add_entry')
def add_entry():
    pass
    
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
                #session['user'] = jsonify(user)
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
