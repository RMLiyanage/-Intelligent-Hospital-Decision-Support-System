"""
routes/patient_routes.py  (full CRUD)
======================================
Roles:
  admin    → Read, Update, Delete
  operator → Create, Read, Update
  doctor   → Read
  patient  → Read
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from routes.auth_routes import login_required, role_required
from database.db import query_db

logger = logging.getLogger(__name__)

patient_bp = Blueprint('patient', __name__, url_prefix='/patients')

_LOCATIONS_SQL = "SELECT id, name, location_type FROM locations ORDER BY name"
_SPECS = ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
          'Emergency Medicine', 'General Surgery', 'Internal Medicine',
          'Obstetrics and Gynecology', 'Radiology']


# ── READ ────────────────────────────────────────────────────────────────────

@patient_bp.route('/my-appointments')
@login_required
def my_appointments():
    """Patient Portal — View active logged in patient's appointment details."""
    pid = session.get('patient_id')
    if not pid:
        flash('No patient record found in active session.', 'warning')
        return redirect(url_for('auth.login'))
    return patient_details(pid)


@patient_bp.route('/')
@login_required
def list_patients():
    if session.get('role') == 'patient':
        return redirect(url_for('patient.my_appointments'))

    patients = query_db("""
        SELECT p.id, p.name, p.phone, p.age, p.gender, p.blood_type,
               p.emergency_level, p.required_specialization, p.created_at,
               l.name AS location_name
        FROM patients p
        LEFT JOIN locations l ON p.location_id = l.id
        ORDER BY p.created_at DESC
    """) or []
    return render_template('patients/list.html', patients=patients)


@patient_bp.route('/<int:pid>')
@patient_bp.route('/<int:pid>/details')
@login_required
def patient_details(pid):
    """View comprehensive patient details including assigned doctor, appointments, and care history."""
    if session.get('role') == 'patient' and session.get('patient_id') != pid:
        pid = session.get('patient_id')

    patient = query_db("""
        SELECT p.*, l.name AS location_name
        FROM patients p
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.id = %s
    """, (pid,), one=True)

    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('patient.list_patients'))

    # Appointments with assigned doctor and hospital
    appointments = query_db("""
        SELECT a.id, a.appointment_date, a.start_time, a.end_time, a.duration_min,
               a.status, a.room_number, a.notes,
               d.id AS doctor_id, d.name AS doctor_name, d.specialization AS doctor_specialization,
               d.qualification AS doctor_qualification,
               h.name AS hospital_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.start_time ASC
    """, (pid,)) or []

    # Recent Emergency Requests
    emergencies = query_db("""
        SELECT er.id, er.emergency_level, er.status, er.created_at,
               h.name AS hospital_name
        FROM emergency_requests er
        LEFT JOIN hospitals h ON er.recommended_hospital_id = h.id
        WHERE er.patient_id = %s
        ORDER BY er.created_at DESC LIMIT 5
    """, (pid,)) or []

    return render_template(
        'patients/view.html',
        patient=patient,
        appointments=appointments,
        emergencies=emergencies
    )


# ── CREATE ───────────────────────────────────────────────────────────────────


@patient_bp.route('/add', methods=['GET'])
@role_required('operator')
def add_patient_form():
    return render_template('patients/add.html',
                           locations=query_db(_LOCATIONS_SQL) or [],
                           specs=_SPECS)


@patient_bp.route('/add', methods=['POST'])
@role_required('operator')
def add_patient():
    name   = request.form.get('name', '').strip()
    phone  = request.form.get('phone', '').strip()
    age    = request.form.get('age', type=int)
    gender = request.form.get('gender', 'M')
    blood  = request.form.get('blood_type', 'O+')
    loc_id = request.form.get('location_id', type=int)
    level  = request.form.get('emergency_level', 'medium')
    spec   = request.form.get('required_specialization', 'Cardiology')

    if not name or not age or not loc_id:
        flash('Name, Age and Location are required.', 'danger')
        return render_template('patients/add.html',
                               locations=query_db(_LOCATIONS_SQL) or [],
                               specs=_SPECS)
    try:
        query_db("""
            INSERT INTO patients (name, phone, age, gender, blood_type, location_id,
                                  emergency_level, required_specialization)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, phone or None, age, gender, blood, loc_id, level, spec))

        new = query_db("SELECT id FROM patients WHERE name=%s ORDER BY id DESC LIMIT 1",
                       (name,), one=True)
        new_id = new['id'] if new else None
        logger.info("Registered patient '%s' (id=%s)", name, new_id)
        flash(f'Patient "{name}" registered. Now complete the appointment request.', 'success')
        return redirect(url_for('emergency.new_emergency', patient_id=new_id))
    except Exception as e:
        logger.error("Failed to register patient: %s", e)
        flash(f'Error: {e}', 'danger')
        return render_template('patients/add.html',
                               locations=query_db(_LOCATIONS_SQL) or [],
                               specs=_SPECS)


# ── UPDATE ───────────────────────────────────────────────────────────────────

@patient_bp.route('/<int:pid>/edit', methods=['GET'])
@role_required('admin', 'operator')
def edit_patient_form(pid):
    p = query_db("SELECT * FROM patients WHERE id=%s", (pid,), one=True)
    if not p:
        flash('Patient not found.', 'danger')
        return redirect(url_for('patient.list_patients'))
    return render_template('patients/edit.html', p=p,
                           locations=query_db(_LOCATIONS_SQL) or [],
                           specs=_SPECS)


@patient_bp.route('/<int:pid>/edit', methods=['POST'])
@role_required('admin', 'operator')
def edit_patient(pid):
    name   = request.form.get('name', '').strip()
    phone  = request.form.get('phone', '').strip()
    age    = request.form.get('age', type=int)
    gender = request.form.get('gender', 'M')
    blood  = request.form.get('blood_type', 'O+')
    loc_id = request.form.get('location_id', type=int)
    level  = request.form.get('emergency_level', 'medium')
    spec   = request.form.get('required_specialization', 'Cardiology')
    try:
        query_db("""
            UPDATE patients SET name=%s, phone=%s, age=%s, gender=%s, blood_type=%s,
            location_id=%s, emergency_level=%s, required_specialization=%s
            WHERE id=%s
        """, (name, phone or None, age, gender, blood, loc_id, level, spec, pid))
        flash(f'Patient "{name}" updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating patient: {e}', 'danger')
    return redirect(url_for('patient.list_patients'))


# ── DELETE ───────────────────────────────────────────────────────────────────

@patient_bp.route('/<int:pid>/delete', methods=['POST'])
@role_required('admin')
def delete_patient(pid):
    p = query_db("SELECT name FROM patients WHERE id=%s", (pid,), one=True)
    if p:
        try:
            query_db("DELETE FROM patients WHERE id=%s", (pid,))
            flash(f'Patient "{p["name"]}" deleted.', 'success')
        except Exception as e:
            flash(f'Error deleting patient: {e}', 'danger')
    else:
        flash('Patient not found.', 'danger')
    return redirect(url_for('patient.list_patients'))
