"""
routes/user_routes.py
=====================
Admin User and Role Management routes:
  - List all users with role statistics
  - Add new user with password hashing and role assignment
  - Edit existing user and update role/password
  - Delete user (with active admin protection)
"""

import logging
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session
)
from werkzeug.security import generate_password_hash

from routes.auth_routes import role_required
from database.db import query_db

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/users')

ROLES = ['admin', 'operator', 'doctor', 'patient']


# ════════════════════════════════════════════════════════════════
# 1. LIST USERS
# ════════════════════════════════════════════════════════════════
@user_bp.route('/')
@role_required('admin')
def list_users():
    """Display user management directory with role counts and search/filter."""
    role_filter = request.args.get('role', '').strip().lower()
    search_query = request.args.get('q', '').strip()

    sql = """
        SELECT u.id, u.name, u.email, u.role, u.doctor_id, u.created_at,
               d.name AS doctor_name, d.specialization AS doctor_specialization,
               h.name AS hospital_name
        FROM users u
        LEFT JOIN doctors d ON u.doctor_id = d.id
        LEFT JOIN hospitals h ON d.hospital_id = h.id
        WHERE 1=1
    """
    params = []
    if role_filter and role_filter in ROLES:
        sql += " AND u.role = %s"
        params.append(role_filter)
    if search_query:
        sql += " AND (u.name LIKE %s OR u.email LIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    sql += " ORDER BY u.id ASC"
    users = query_db(sql, tuple(params)) or []

    # Calculate role breakdown
    role_stats = {
        'admin': 0,
        'operator': 0,
        'doctor': 0,
        'patient': 0,
        'total': 0
    }
    all_users = query_db("SELECT role, COUNT(*) AS count FROM users GROUP BY role") or []
    for r in all_users:
        if r['role'] in role_stats:
            role_stats[r['role']] = r['count']
        role_stats['total'] += r['count']

    return render_template(
        'users/list.html',
        users=users,
        role_stats=role_stats,
        role_filter=role_filter,
        search_query=search_query,
        roles=ROLES,
    )


# ════════════════════════════════════════════════════════════════
# 2. CREATE USER
# ════════════════════════════════════════════════════════════════
@user_bp.route('/add', methods=['GET', 'POST'])
@role_required('admin')
def add_user():
    """Create a new system user with assigned role."""
    doctors = query_db("""
        SELECT d.id, d.name, d.specialization, h.name AS hospital_name
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY d.name
    """) or []

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'patient').strip().lower()
        doctor_id = request.form.get('doctor_id', type=int) if role == 'doctor' else None

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return render_template('users/form.html', mode='add', user=None, roles=ROLES, doctors=doctors)

        if role not in ROLES:
            flash('Invalid user role selected.', 'danger')
            return render_template('users/form.html', mode='add', user=None, roles=ROLES, doctors=doctors)

        # Check for duplicate email
        existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
        if existing:
            flash(f'A user with email "{email}" already exists.', 'danger')
            return render_template('users/form.html', mode='add', user=None, roles=ROLES, doctors=doctors)

        try:
            pw_hash = generate_password_hash(password)
            query_db("""
                INSERT INTO users (name, email, password_hash, role, doctor_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, pw_hash, role, doctor_id))

            logger.info("Admin created new user '%s' (%s, role=%s)", name, email, role)
            flash(f'User "{name}" created successfully with role "{role.title()}".', 'success')
            return redirect(url_for('user.list_users'))
        except Exception as e:
            logger.error("Failed to create user: %s", e)
            flash(f'Error creating user: {e}', 'danger')

    return render_template('users/form.html', mode='add', user=None, roles=ROLES, doctors=doctors)


# ════════════════════════════════════════════════════════════════
# 3. EDIT USER & ROLE
# ════════════════════════════════════════════════════════════════
@user_bp.route('/<int:uid>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_user(uid: int):
    """Edit existing user details, update role or change password."""
    user = query_db("SELECT id, name, email, role, doctor_id FROM users WHERE id = %s", (uid,), one=True)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('user.list_users'))

    doctors = query_db("""
        SELECT d.id, d.name, d.specialization, h.name AS hospital_name
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY d.name
    """) or []

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'patient').strip().lower()
        new_password = request.form.get('password', '').strip()
        doctor_id = request.form.get('doctor_id', type=int) if role == 'doctor' else None

        if not name or not email:
            flash('Name and email are required.', 'danger')
            return render_template('users/form.html', mode='edit', user=user, roles=ROLES, doctors=doctors)

        if role not in ROLES:
            flash('Invalid user role selected.', 'danger')
            return render_template('users/form.html', mode='edit', user=user, roles=ROLES, doctors=doctors)

        # Protect against self-demoting the active admin if it's their own account
        current_admin_id = session.get('user_id')
        if current_admin_id == uid and role != 'admin':
            flash('You cannot remove the admin role from your own currently active account.', 'warning')
            role = 'admin'

        # Check duplicate email
        dup = query_db("SELECT id FROM users WHERE email = %s AND id != %s", (email, uid), one=True)
        if dup:
            flash(f'Email "{email}" is already used by another user.', 'danger')
            return render_template('users/form.html', mode='edit', user=user, roles=ROLES, doctors=doctors)

        try:
            if new_password:
                pw_hash = generate_password_hash(new_password)
                query_db("""
                    UPDATE users
                    SET name = %s, email = %s, role = %s, doctor_id = %s, password_hash = %s
                    WHERE id = %s
                """, (name, email, role, doctor_id, pw_hash, uid))
            else:
                query_db("""
                    UPDATE users
                    SET name = %s, email = %s, role = %s, doctor_id = %s
                    WHERE id = %s
                """, (name, email, role, doctor_id, uid))

            # Update active session name if editing self
            if session.get('user_id') == uid:
                session['user_name'] = name
                session['user_email'] = email
                session['role'] = role

            logger.info("Admin updated user #%d (%s, role=%s)", uid, email, role)
            flash(f'User "{name}" updated successfully.', 'success')
            return redirect(url_for('user.list_users'))
        except Exception as e:
            logger.error("Failed to update user: %s", e)
            flash(f'Error updating user: {e}', 'danger')

    return render_template('users/form.html', mode='edit', user=user, roles=ROLES, doctors=doctors)


# ════════════════════════════════════════════════════════════════
# 4. DELETE USER
# ════════════════════════════════════════════════════════════════
@user_bp.route('/<int:uid>/delete', methods=['POST'])
@role_required('admin')
def delete_user(uid: int):
    """Delete a user from the system."""
    # Prevent self-deletion
    if session.get('user_id') == uid:
        flash('You cannot delete your own currently logged-in admin account.', 'danger')
        return redirect(url_for('user.list_users'))

    user = query_db("SELECT name FROM users WHERE id = %s", (uid,), one=True)
    if user:
        try:
            query_db("DELETE FROM users WHERE id = %s", (uid,))
            logger.info("Admin deleted user #%d (%s)", uid, user['name'])
            flash(f'User "{user["name"]}" was deleted successfully.', 'success')
        except Exception as e:
            logger.error("Failed to delete user: %s", e)
            flash(f'Error deleting user: {e}', 'danger')
    else:
        flash('User not found.', 'danger')

    return redirect(url_for('user.list_users'))
