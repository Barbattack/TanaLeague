# -*- coding: utf-8 -*-
"""
TanaLeague Admin Authentication
================================

Sistema di autenticazione per admin panel.
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from config import ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_TIMEOUT


def login_user(username, password):
    """
    Verifica credenziali e crea sessione admin.

    Args:
        username (str): Username inserito
        password (str): Password inserita

    Returns:
        bool: True se login riuscito, False altrimenti
    """
    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session['admin_logged_in'] = True
        session['admin_username'] = username
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True  # Usa PERMANENT_SESSION_LIFETIME
        return True
    return False


def logout_user():
    """
    Effettua logout e pulisce sessione.
    """
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('login_time', None)


def is_admin_logged_in():
    """
    Verifica se admin è loggato e sessione valida.

    Returns:
        bool: True se loggato e sessione valida, False altrimenti
    """
    if not session.get('admin_logged_in'):
        return False

    # Check session timeout
    login_time_str = session.get('login_time')
    if login_time_str:
        login_time = datetime.fromisoformat(login_time_str)
        if datetime.now() - login_time > timedelta(minutes=SESSION_TIMEOUT):
            logout_user()
            return False

    return True


def admin_required(f):
    """
    Decorator per proteggere routes admin.

    Uso:
        @app.route('/admin/dashboard')
        @admin_required
        def admin_dashboard():
            return render_template('admin.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            flash('Accesso negato. Effettua il login.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def get_session_info():
    """
    Ottiene info sulla sessione corrente.

    Returns:
        dict: Info sessione (username, login_time, expires_in)
    """
    if not is_admin_logged_in():
        return None

    login_time_str = session.get('login_time')
    if login_time_str:
        login_time = datetime.fromisoformat(login_time_str)
        elapsed = datetime.now() - login_time
        remaining = timedelta(minutes=SESSION_TIMEOUT) - elapsed

        return {
            'username': session.get('admin_username'),
            'login_time': login_time,
            'expires_in_minutes': int(remaining.total_seconds() / 60)
        }

    return None
