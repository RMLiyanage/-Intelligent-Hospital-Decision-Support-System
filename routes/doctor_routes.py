"""
routes/doctor_routes.py
========================
Doctor portal routes: doctor dashboard, appointment management, status updates.

Roles:
  doctor → Doctor Portal (view and manage assigned patient appointments)
  admin  → Full access to doctor portal
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from routes.auth_routes import login_required, role_required
from database.db import query_db

logger = logging.getLogger(__name__)

doctor_bp = Blueprint('doctor', __name__)


def _get_current_doctor():
    """Helper to retrieve doctor record for logged-in user or first doctor if admin."""
    doc_id = session.get('doctor_id')
    if doc_id:
        doc = query_db("""
            SELECT d.*, h.name AS hospital_name 
            FROM doctors d 
            JOIN hospitals h ON d.hospital_id = h.id 
            WHERE d.id = %s
        """, (doc_id,), one=True)
        if doc:
            return doc

    # Fallback for admin or if doctor_id not directly set
    user_email = session.get('user_email', '')
    doc = query_db("""
        SELECT d.*, h.name AS hospital_name 
        FROM doctors d 
        JOIN hospitals h ON d.hospital_id = h.id 
        WHERE LOWER(d.name) LIKE %s OR d.id = 1
        ORDER BY d.id ASC LIMIT 1
    """, (f"%{session.get('user_name', '')}%",), one=True)
    return doc


@doctor_bp.route('/doctor/dashboard')
@login_required
@role_required('doctor', 'admin')
def dashboard():
    """Doctor Portal Dashboard — Overview of doctor schedule, stats, and today's appointments."""
    doctor = _get_current_doctor()
    if not doctor:
        flash('No doctor profile associated with your user account.', 'warning')
        return redirect(url_for('dashboard.index'))

    doc_id = doctor['id']

    # Statistics
    stats = {}
    stats['total_appointments'] = (
        query_db("SELECT COUNT(*) AS c FROM appointments WHERE doctor_id = %s", (doc_id,), one=True) or {}
    ).get('c', 0)

    stats['today_appointments'] = (
        query_db("SELECT COUNT(*) AS c FROM appointments WHERE doctor_id = %s AND appointment_date = CURDATE()", (doc_id,), one=True) or {}
    ).get('c', 0)

    stats['pending_appointments'] = (
        query_db("SELECT COUNT(*) AS c FROM appointments WHERE doctor_id = %s AND status = 'pending'", (doc_id,), one=True) or {}
    ).get('c', 0)

    stats['completed_appointments'] = (
        query_db("SELECT COUNT(*) AS c FROM appointments WHERE doctor_id = %s AND status = 'completed'", (doc_id,), one=True) or {}
    ).get('c', 0)

    # Today's appointments
    today_appts = query_db("""
        SELECT a.id, a.appointment_date, a.start_time, a.end_time, a.duration_min,
               a.status, a.room_number, a.notes,
               p.id AS patient_id, p.name AS patient_name, p.age, p.gender,
               p.emergency_level, p.blood_type, p.phone, p.required_specialization,
               h.name AS hospital_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.doctor_id = %s AND a.appointment_date = CURDATE()
        ORDER BY a.start_time ASC
    """, (doc_id,)) or []

    # Upcoming/Recent appointments (limit 10)
    recent_appts = query_db("""
        SELECT a.id, a.appointment_date, a.start_time, a.end_time, a.duration_min,
               a.status, a.room_number, a.notes,
               p.id AS patient_id, p.name AS patient_name, p.age, p.gender,
               p.emergency_level, p.blood_type, p.phone, p.required_specialization,
               h.name AS hospital_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date DESC, a.start_time ASC
        LIMIT 10
    """, (doc_id,)) or []

    return render_template(
        'doctor/dashboard.html',
        doctor=doctor,
        stats=stats,
        today_appts=today_appts,
        recent_appts=recent_appts
    )


@doctor_bp.route('/doctor/appointments')
@login_required
@role_required('doctor', 'admin')
def list_appointments():
    """All appointments view for doctor with filtering."""
    doctor = _get_current_doctor()
    if not doctor:
        flash('No doctor profile associated with your account.', 'warning')
        return redirect(url_for('dashboard.index'))

    doc_id = doctor['id']
    status_filter = request.args.get('status', 'all')

    sql = """
        SELECT a.id, a.appointment_date, a.start_time, a.end_time, a.duration_min,
               a.status, a.room_number, a.notes,
               p.id AS patient_id, p.name AS patient_name, p.age, p.gender,
               p.emergency_level, p.blood_type, p.phone, p.required_specialization,
               h.name AS hospital_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.doctor_id = %s
    """
    params = [doc_id]

    if status_filter != 'all':
        sql += " AND a.status = %s"
        params.append(status_filter)

    sql += " ORDER BY a.appointment_date DESC, a.start_time ASC"

    appointments = query_db(sql, tuple(params)) or []

    return render_template(
        'doctor/appointments.html',
        doctor=doctor,
        appointments=appointments,
        current_status=status_filter
    )


@doctor_bp.route('/doctor/appointments/<int:appt_id>/update', methods=['POST'])
@login_required
@role_required('doctor', 'admin')
def update_appointment(appt_id):
    """Update appointment status and doctor notes."""
    doctor = _get_current_doctor()
    if not doctor:
        flash('Permission denied.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Verify appointment belongs to this doctor (or admin)
    appt = query_db("SELECT id, doctor_id FROM appointments WHERE id = %s", (appt_id,), one=True)
    if not appt:
        flash('Appointment not found.', 'danger')
        return redirect(url_for('doctor.list_appointments'))

    if session.get('role') != 'admin' and appt['doctor_id'] != doctor['id']:
        flash('You can only update your own appointments.', 'danger')
        return redirect(url_for('doctor.list_appointments'))

    new_status = request.form.get('status')
    notes = request.form.get('notes', '').strip()

    valid_statuses = ['scheduled', 'completed', 'cancelled', 'pending']
    if new_status not in valid_statuses:
        flash('Invalid status provided.', 'danger')
        return redirect(url_for('doctor.list_appointments'))

    try:
        query_db("""
            UPDATE appointments 
            SET status = %s, notes = %s 
            WHERE id = %s
        """, (new_status, notes, appt_id))
        flash(f'Appointment #{appt_id} updated successfully.', 'success')
    except Exception as e:
        logger.error("Failed to update appointment #%s: %s", appt_id, e)
        flash(f'Error updating appointment: {e}', 'danger')

    redirect_target = request.referrer or url_for('doctor.list_appointments')
    return redirect(redirect_target)


@doctor_bp.route('/doctor/schedules', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'operator', 'doctor')
def manage_daily_schedules():
    """Manage doctors daily working schedules, availability status, and time slots."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_doctor_status':
            doc_id = request.form.get('doctor_id', type=int)
            new_status = request.form.get('availability_status')
            valid_statuses = ['available', 'busy', 'off_duty']
            if doc_id and new_status in valid_statuses:
                query_db("UPDATE doctors SET availability_status = %s WHERE id = %s", (new_status, doc_id))
                flash("Doctor availability status updated successfully.", "success")
            else:
                flash("Invalid doctor or status provided.", "danger")
            return redirect(request.referrer or url_for('doctor.manage_daily_schedules'))

        elif action == 'update_appointment_status':
            appt_id = request.form.get('appointment_id', type=int)
            new_status = request.form.get('status')
            notes = request.form.get('notes', '').strip()
            valid_statuses = ['scheduled', 'completed', 'cancelled', 'pending']
            if appt_id and new_status in valid_statuses:
                query_db("UPDATE appointments SET status = %s, notes = %s WHERE id = %s", (new_status, notes, appt_id))
                flash(f"Schedule slot #{appt_id} updated successfully.", "success")
            else:
                flash("Invalid appointment or status provided.", "danger")
            return redirect(request.referrer or url_for('doctor.manage_daily_schedules'))

    # GET request filtering
    selected_date_str = request.args.get('date')
    selected_doc_id = request.args.get('doctor_id', type=int)

    if not selected_date_str:
        from datetime import date
        selected_date_str = date.today().strftime('%Y-%m-%d')

    # Fetch all doctors with hospital info
    doctors = query_db("""
        SELECT d.*, h.name AS hospital_name
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY d.name ASC
    """) or []

    # Fetch appointments for the selected date (and optional doctor filter)
    sql = """
        SELECT a.id, a.appointment_date, a.start_time, a.end_time, a.duration_min,
               a.status, a.room_number, a.notes,
               d.id AS doctor_id, d.name AS doctor_name, d.specialization AS doctor_specialization,
               d.qualification AS doctor_qualification, d.availability_status AS doctor_availability,
               p.id AS patient_id, p.name AS patient_name, p.age, p.gender, p.phone,
               h.name AS hospital_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN patients p ON a.patient_id = p.id
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.appointment_date = %s
    """
    params = [selected_date_str]
    if selected_doc_id:
        sql += " AND a.doctor_id = %s"
        params.append(selected_doc_id)

    sql += " ORDER BY a.start_time ASC"

    schedules = query_db(sql, tuple(params)) or []

    return render_template(
        'doctor/schedules.html',
        doctors=doctors,
        schedules=schedules,
        selected_date=selected_date_str,
        selected_doctor_id=selected_doc_id
    )
