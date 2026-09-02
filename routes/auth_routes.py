"""
routes/auth_routes.py
======================
Authentication routes: login, logout.

Roles:
  admin    → /dashboard (full access)
  operator → /dashboard
  doctor   → /doctor/dashboard
  patient  → /dashboard

Session keys set on login:
  session['user_id']   : int
  session['user_name'] : str
  session['user_email']: str
  session['role']      : str
"""

import logging
from functools import wraps

from flask import (Blueprint, flash, redirect, render_template,
                   request, session, url_for, jsonify, current_app)
from werkzeug.security import check_password_hash

from database.db import query_db

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


# ============================================================
# Role-based access decorator
# ============================================================

def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """Restrict access to users with specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# Routes
# ============================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and form handler."""
    # Already logged in
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        user = query_db(
            'SELECT id, name, email, password_hash, role, doctor_id FROM users WHERE email = %s',
            (email,),
            one=True,
        )

        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'danger')
            logger.warning("Failed login attempt for email: %s", email)
            return render_template('auth/login.html')

        # Successful login
        session.permanent = True
        session['user_id']    = user['id']
        session['user_name']  = user['name']
        session['user_email'] = user['email']
        session['role']       = user['role']
        session['doctor_id']  = user.get('doctor_id')

        logger.info("User %s (%s) logged in.", user['email'], user['role'])
        flash(f"Welcome, {user['name']}!", 'success')

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user['role'] == 'doctor':
            return redirect(url_for('doctor.dashboard'))

        return redirect(url_for('dashboard.index'))


    return render_template('auth/login.html')


def _has_nic_column():
    """Ensure nic column exists in patients table or check availability."""
    try:
        from database.db import execute_db
        cols = query_db("SHOW COLUMNS FROM patients") or []
        col_names = [c['Field'].lower() for c in cols if 'Field' in c]
        if 'nic' not in col_names:
            try:
                execute_db("ALTER TABLE patients ADD COLUMN nic VARCHAR(20) NULL")
                return True
            except Exception:
                return False
        return True
    except Exception:
        return False


@auth_bp.route('/patient-login', methods=['GET', 'POST'])
def patient_login():
    """Authenticate patient via Patient Name + Phone Number."""
    if request.method == 'POST':
        name = request.form.get('patient_name', '').strip()
        phone = request.form.get('phone_number', request.form.get('identity_number', '')).strip()

        if not name or not phone:
            flash('Please enter both Patient Name and Phone Number.', 'danger')
            return redirect(url_for('auth.login'))

        has_nic = _has_nic_column()

        if has_nic:
            patient = query_db('''
                SELECT p.id, p.name, p.phone
                FROM patients p
                WHERE LOWER(TRIM(p.name)) = LOWER(TRIM(%s))
                  AND (
                    (p.phone IS NOT NULL AND LOWER(TRIM(p.phone)) = LOWER(TRIM(%s)))
                    OR (p.nic IS NOT NULL AND LOWER(TRIM(p.nic)) = LOWER(TRIM(%s)))
                    OR (CAST(p.id AS CHAR) = %s)
                  )
            ''', (name, phone, phone, phone), one=True)

            if not patient:
                patient = query_db('''
                    SELECT p.id, p.name, p.phone
                    FROM patients p
                    WHERE LOWER(p.name) LIKE LOWER(%s)
                      AND (
                        (p.phone IS NOT NULL AND p.phone LIKE %s)
                        OR (CAST(p.id AS CHAR) = %s)
                      )
                ''', (f"%{name}%", f"%{phone}%", phone), one=True)
        else:
            patient = query_db('''
                SELECT p.id, p.name, p.phone
                FROM patients p
                WHERE LOWER(TRIM(p.name)) = LOWER(TRIM(%s))
                  AND (
                    (p.phone IS NOT NULL AND LOWER(TRIM(p.phone)) = LOWER(TRIM(%s)))
                    OR (CAST(p.id AS CHAR) = %s)
                  )
            ''', (name, phone, phone), one=True)

            if not patient:
                patient = query_db('''
                    SELECT p.id, p.name, p.phone
                    FROM patients p
                    WHERE LOWER(p.name) LIKE LOWER(%s)
                      AND (
                        (p.phone IS NOT NULL AND p.phone LIKE %s)
                        OR (CAST(p.id AS CHAR) = %s)
                      )
                ''', (f"%{name}%", f"%{phone}%", phone), one=True)

        if not patient:
            flash('No matching patient record found. Please check your Name and Phone Number.', 'danger')
            logger.warning("Failed patient login attempt for Name: %s, Phone: %s", name, phone)
            return redirect(url_for('auth.login'))

        # Successful Patient Login
        session.permanent = True
        session['user_id'] = f"patient_{patient['id']}"
        session['patient_id'] = patient['id']
        session['user_name'] = patient['name']
        session['role'] = 'patient'

        logger.info("Patient '%s' (ID: %s) authenticated.", patient['name'], patient['id'])
        flash(f"Welcome, {patient['name']}! Here are your appointment details.", 'success')
        return redirect(url_for('patient.my_appointments'))

    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    name = session.get('user_name', 'User')
    session.clear()
    flash(f'You have been logged out, {name}.', 'info')
    return redirect(url_for('auth.login'))
