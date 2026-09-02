"""
routes/dashboard_routes.py
===========================
Dashboard route — system overview with live DB stats.
"""

import logging
from flask import Blueprint, render_template, session, redirect, url_for

from routes.auth_routes import login_required
from database.db import query_db

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main dashboard — stats cards, recent requests, recent algorithm runs."""
    if session.get('role') == 'doctor':
        return redirect(url_for('doctor.dashboard'))
    if session.get('role') == 'patient':
        return redirect(url_for('patient.my_appointments'))

    # ---- Live stats from database ----

    stats = {}

    stats['total_hospitals'] = (
        query_db('SELECT COUNT(*) AS c FROM hospitals WHERE status = %s',
                 ('active',), one=True) or {}
    ).get('c', 0)

    stats['available_doctors'] = (
        query_db('SELECT COUNT(*) AS c FROM doctors WHERE availability_status = %s',
                 ('available',), one=True) or {}
    ).get('c', 0)

    stats['total_icu_available'] = (
        query_db('SELECT SUM(available_icu_beds) AS c FROM hospitals WHERE status = %s',
                 ('active',), one=True) or {}
    ).get('c', 0) or 0

    stats['pending_emergencies'] = (
        query_db('SELECT COUNT(*) AS c FROM emergency_requests WHERE status IN (%s,%s)',
                 ('pending', 'processing'), one=True) or {}
    ).get('c', 0)

    stats['total_patients'] = (
        query_db('SELECT COUNT(*) AS c FROM patients', one=True) or {}
    ).get('c', 0)

    stats['algorithm_runs_today'] = (
        query_db('SELECT COUNT(*) AS c FROM algorithm_results WHERE DATE(created_at) = CURDATE()',
                 one=True) or {}
    ).get('c', 0)

    # ---- Recent emergency requests ----
    recent_emergencies = query_db(
        '''SELECT er.id, er.emergency_level, er.status, er.created_at,
                  p.name AS patient_name, l.name AS location_name,
                  h.name AS hospital_name
           FROM emergency_requests er
           JOIN patients p  ON er.patient_id = p.id
           LEFT JOIN locations l ON er.source_location_id = l.id
           LEFT JOIN hospitals h ON er.recommended_hospital_id = h.id
           ORDER BY er.created_at DESC LIMIT 10'''
    ) or []

    # ---- Recent algorithm results ----
    recent_algorithms = query_db(
        '''SELECT module, algorithm, execution_time_ms, solution_quality,
                  input_size, created_at
           FROM algorithm_results
           ORDER BY created_at DESC LIMIT 8'''
    ) or []

    # ---- Hospital status overview ----
    hospitals_overview = query_db(
        '''SELECT h.name, h.available_beds, h.capacity, h.available_icu_beds,
                  h.icu_beds, h.status, h.rating, l.name AS city
           FROM hospitals h
           JOIN locations l ON h.location_id = l.id
           ORDER BY h.rating DESC'''
    ) or []

    # ---- Patients & Locations for Quick Emergency Dispatch ----
    patients_list = query_db("SELECT id, name, age, emergency_level, location_id, required_specialization FROM patients ORDER BY name LIMIT 50") or []

    locations_list = query_db("SELECT id, name, location_type FROM locations ORDER BY name") or []

    return render_template(
        'dashboard/index.html',
        stats=stats,
        recent_emergencies=recent_emergencies,
        recent_algorithms=recent_algorithms,
        hospitals_overview=hospitals_overview,
        patients_list=patients_list,
        locations_list=locations_list,
    )

