"""
routes/emergency_routes.py
===========================
Emergency Request routes — 7-step IDSS pipeline wizard & visual result page.

Routes:
  GET  /emergency/new       — Emergency Request Form (Patient selection, location, specialization)
  POST /emergency/create    — Executes process_emergency_pipeline(), redirects to result
  GET  /emergency/<id>      — Step-by-step visual pipeline results page
  POST /emergency/<id>/book — Process ambulance booking and payment
"""

import json
import logging
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, session)

from routes.auth_routes import login_required, role_required
from database.db import query_db
from services.emergency_service import process_emergency_pipeline

logger = logging.getLogger(__name__)

emergency_bp = Blueprint('emergency', __name__, url_prefix='/emergency')


@emergency_bp.route('/new', methods=['GET'])
@role_required('operator', 'patient')
def new_emergency():
    """Appointment Request Form — supports ?patient_id=X to pre-select a just-registered patient."""
    patients = query_db("SELECT id, name, age, emergency_level, location_id, required_specialization FROM patients ORDER BY name") or []

    locations = query_db("SELECT id, name, location_type FROM locations ORDER BY name") or []
    specializations = [
        'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
        'Emergency Medicine', 'General Surgery', 'Internal Medicine',
        'Obstetrics and Gynecology', 'Radiology'
    ]

    # Pre-select patient if coming from the patient registration flow
    preselect_patient_id = request.args.get('patient_id', type=int)

    return render_template(
        'emergency/new.html',
        patients=patients,
        locations=locations,
        specializations=specializations,
        preselect_patient_id=preselect_patient_id,
    )


@emergency_bp.route('/create', methods=['POST'])
@role_required('operator', 'patient')
def create_emergency():
    """Execute the full 7-step IDSS pipeline for the submitted request."""
    patient_id = request.form.get('patient_id', type=int)
    caller_name = request.form.get('caller_name', '').strip()
    emergency_level = request.form.get('emergency_level', 'critical')
    specialization = request.form.get('required_specialization', 'Cardiology')
    location_id = request.form.get('source_location_id', type=int)
    preferred_date = request.form.get('preferred_date')
    preferred_time_slot = request.form.get('preferred_time_slot', 'morning')
    require_amb_raw = request.form.get('require_ambulance', 'yes')
    require_ambulance = str(require_amb_raw).lower() in ('yes', 'true', '1', 'on')

    if not patient_id and caller_name:
        existing = query_db("SELECT id FROM patients WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))", (caller_name,), one=True)
        if existing:
            patient_id = existing['id']
        else:
            from database.db import execute_db
            patient_id = execute_db(
                "INSERT INTO patients (name, age, gender, emergency_level, location_id, required_specialization) VALUES (%s, %s, %s, %s, %s, %s)",
                (caller_name, 35, 'M', emergency_level, location_id, specialization)
            )

    if not patient_id:
        flash('Please select a registered patient or enter a caller/patient name.', 'danger')
        return redirect(request.referrer or url_for('emergency.new_emergency'))

    try:
        pipeline_res = process_emergency_pipeline(
            patient_id=patient_id,
            emergency_level=emergency_level,
            required_specialization=specialization,
            source_location_id=location_id,
            preferred_date=preferred_date,
            preferred_time_slot=preferred_time_slot,
            created_by_user_id=session.get('user_id'),
            require_ambulance=require_ambulance,
        )


        er_id = pipeline_res['emergency_request_id']
        flash('Emergency request processed successfully through 5-module pipeline!', 'success')
        return redirect(url_for('emergency.view_emergency', er_id=er_id))

    except Exception as e:
        logger.error("Error creating emergency request: %s", e)
        flash(f"Failed to process emergency request: {e}", 'danger')
        return redirect(url_for('emergency.new_emergency'))


@emergency_bp.route('/<int:er_id>', methods=['GET'])
@login_required
def view_emergency(er_id: int):
    """View step-by-step visual results of an emergency request pipeline."""
    row = query_db(
        """SELECT er.id, er.patient_id, er.emergency_level, er.required_specialization,
                  er.source_location_id, er.status, er.result_json, er.created_at,
                  p.name AS patient_name, p.age AS patient_age, p.blood_type,
                  l.name AS location_name, h.name AS hospital_name
           FROM emergency_requests er
           JOIN patients p ON er.patient_id = p.id
           LEFT JOIN locations l ON er.source_location_id = l.id
           LEFT JOIN hospitals h ON er.recommended_hospital_id = h.id
           WHERE er.id = %s""",
        (er_id,),
        one=True,
    )

    if not row:
        flash('Emergency request not found.', 'danger')
        return redirect(url_for('dashboard.index'))

    pipeline_data = {}
    if row.get('result_json'):
        try:
            pipeline_data = json.loads(row['result_json'])
        except Exception as e:
            logger.error("Failed to parse result_json for ER #%d: %s", er_id, e)

    # Fetch source location coordinates
    source_loc = None
    if row.get('source_location_id'):
        source_loc = query_db("""
            SELECT id, name, latitude, longitude FROM locations WHERE id = %s
        """, (row['source_location_id'],), one=True)

    # Fetch hospital location coordinates
    rec_h = (pipeline_data.get('step_1_decision') or {}).get('recommended_hospital') or {}
    hid = rec_h.get('hospital_id') or row.get('recommended_hospital_id') or 1
    hospital_loc = query_db("""
        SELECT h.id, h.name, h.address, h.rating, l.name AS city, l.latitude, l.longitude
        FROM hospitals h
        JOIN locations l ON h.location_id = l.id
        WHERE h.id = %s
    """, (hid,), one=True)

    # Fetch intermediate path node coordinates for realistic network route
    route_data = pipeline_data.get('step_1_route') or pipeline_data.get('step_4_route') or {}
    path_nodes = route_data.get('path_nodes') or []
    path_coords = []
    if path_nodes:
        placeholders = ', '.join(['%s'] * len(path_nodes))
        rows = query_db(f"SELECT name, latitude, longitude FROM locations WHERE name IN ({placeholders})", tuple(path_nodes)) or []
        node_map = {r['name']: [float(r['latitude']), float(r['longitude'])] for r in rows}
        for node_name in path_nodes:
            if node_name in node_map:
                path_coords.append(node_map[node_name])

    # Fetch available matching doctor for this hospital
    spec = row.get('required_specialization')
    assigned_doctor = None
    if spec:
        assigned_doctor = query_db("""
            SELECT id, name, specialization, qualification, rating, experience_years, availability_status
            FROM doctors
            WHERE hospital_id = %s AND specialization = %s AND availability_status = 'available'
            ORDER BY rating DESC, experience_years DESC LIMIT 1
        """, (hid, spec), one=True)
    if not assigned_doctor:
        assigned_doctor = query_db("""
            SELECT id, name, specialization, qualification, rating, experience_years, availability_status
            FROM doctors
            WHERE hospital_id = %s AND availability_status = 'available'
            ORDER BY rating DESC, experience_years DESC LIMIT 1
        """, (hid,), one=True)

    return render_template(
        'emergency/view.html',
        request_row=row,
        pipeline=pipeline_data,
        source_loc=source_loc,
        hospital_loc=hospital_loc,
        path_coords=path_coords,
        assigned_doctor=assigned_doctor,
    )


@emergency_bp.route('/<int:er_id>/confirm', methods=['POST'])
@login_required
def confirm_care_plan(er_id: int):
    """Confirm care plan and mark emergency request & appointment as confirmed."""
    try:
        query_db("UPDATE emergency_requests SET status = 'completed' WHERE id = %s", (er_id,))
        req = query_db("SELECT patient_id FROM emergency_requests WHERE id = %s", (er_id,), one=True)
        if req:
            query_db("""
                UPDATE appointments 
                SET status = 'scheduled' 
                WHERE patient_id = %s AND status = 'pending'
            """, (req['patient_id'],))

        flash('Care plan and appointment booking confirmed successfully!', 'success')
    except Exception as e:
        logger.error("Error confirming care plan #%d: %s", er_id, e)
        flash(f'Failed to confirm care plan: {e}', 'danger')

    return redirect(url_for('emergency.view_emergency', er_id=er_id))


