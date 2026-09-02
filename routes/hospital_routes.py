"""
routes/hospital_routes.py  (full CRUD)
=======================================
Roles:
  admin    → CRUD on hospitals, doctors, resources
  operator → CRU  on hospitals, doctors, resources
  doctor   → R only
  patient  → R only
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from routes.auth_routes import login_required, role_required
from database.db import query_db, execute_db, get_db

logger = logging.getLogger(__name__)

hospital_bp = Blueprint('hospital', __name__)


def _ensure_hemas_hospitals():
    """Ensure database has all Hemas Hospital branches in Sri Lanka, including Colombo."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM hospitals WHERE name = 'Hemas Hospital - Colombo (Main Branch)' LIMIT 1")
            colombo_exists = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) AS c FROM hospitals WHERE name LIKE 'Hemas%'")
            row = cursor.fetchone()
            if colombo_exists and row and row.get('c', 0) >= 6:
                return  # Already configured

            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("DELETE FROM resources")
            cursor.execute("DELETE FROM appointments WHERE hospital_id > 6 OR doctor_id > 36")
            cursor.execute("DELETE FROM emergency_requests WHERE recommended_hospital_id > 6")
            cursor.execute("DELETE FROM doctors")
            cursor.execute("DELETE FROM hospitals")

            hemas_hospitals = [
                (1, 'Hemas Hospital - Colombo (Main Branch)', 1, '150 Galle Road, Colombo 03', 150, 55, 20, 7, 4.9, 'active', '08:00:00', '20:00:00', 18),
                (2, 'Hemas Hospital - Thalawathugoda', 1, '647 Pannipitiya Road, Thalawathugoda', 100, 38, 14, 5, 4.7, 'active', '08:00:00', '20:00:00', 25),
                (3, 'Hemas Hospital - Wattala', 6, '390 Negombo Road, Wattala', 130, 45, 18, 6, 4.8, 'active', '08:00:00', '20:00:00', 20),
                (4, 'Hemas Hospital - Galle', 16, 'Colombo Road, Kaluwella, Galle', 80, 28, 10, 4, 4.6, 'active', '08:00:00', '20:00:00', 22),
                (5, 'Hemas Hospital - Kandy', 8, 'William Gopallawa Mawatha, Kandy', 90, 32, 12, 4, 4.5, 'active', '08:00:00', '20:00:00', 24),
                (6, 'Hemas Hospital - Kurunegala', 11, 'Colombo Road, Kurunegala', 75, 25, 8, 3, 4.4, 'active', '08:00:00', '20:00:00', 28),
            ]
            for h in hemas_hospitals:
                cursor.execute("""
                    INSERT INTO hospitals (id, name, location_id, address, capacity, available_beds,
                                           icu_beds, available_icu_beds, rating, status,
                                           opening_time, closing_time, avg_wait_time_min)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, h)

            hemas_doctors = [
                # Hemas Colombo (1)
                (1, 'Dr. Pradeep Jayawardena', 'Cardiology', 'MBBS, MD, FRCP (Consultant Cardiologist)', 1, 4.9, 18, 'available', '08:00:00', '17:00:00', 30, 20),
                (2, 'Dr. Nimali Fernando', 'Neurology', 'MBBS, MD (Consultant Neurologist)', 1, 4.8, 15, 'available', '09:00:00', '16:00:00', 30, 18),
                (3, 'Dr. Ashan Perera', 'Emergency Medicine', 'MBBS, MRCEM (Emergency Specialist)', 1, 4.9, 12, 'available', '00:00:00', '23:59:59', 20, 30),
                (4, 'Dr. Kumari Dissanayake', 'Pediatrics', 'MBBS, DCH, MD (Consultant Pediatrician)', 1, 4.7, 20, 'available', '08:30:00', '16:30:00', 30, 25),
                (5, 'Dr. Thilak Weerasinghe', 'General Surgery', 'MBBS, MS, FRCS (Consultant Surgeon)', 1, 4.6, 9, 'available', '09:00:00', '17:00:00', 30, 15),
                (6, 'Dr. Sandya Rajapaksa', 'Obstetrics and Gynecology', 'MBBS, MS, MRCOG (Consultant VOG)', 1, 4.7, 14, 'available', '08:00:00', '15:00:00', 30, 20),

                # Hemas Thalawathugoda (2)
                (7, 'Dr. Chamara Rathnayake', 'Cardiology', 'MBBS, MD (Consultant Cardiologist)', 2, 4.7, 16, 'available', '08:00:00', '17:00:00', 30, 20),
                (8, 'Dr. Sachini Kodagoda', 'Neurology', 'MBBS, MD (Consultant Neurologist)', 2, 4.4, 10, 'available', '09:00:00', '16:00:00', 30, 15),
                (9, 'Dr. Harsha Amarasinghe', 'Emergency Medicine', 'MBBS, MD (Emergency Medicine)', 2, 4.8, 13, 'available', '00:00:00', '23:59:59', 20, 30),
                (10, 'Dr. Mahesh Gunasekara', 'Internal Medicine', 'MBBS, MD, FRCP (Consultant Physician)', 2, 4.5, 11, 'available', '08:30:00', '16:30:00', 30, 20),
                (11, 'Dr. Ruwan Bandara', 'Orthopedics', 'MBBS, MS (Consultant Orthopedic Surgeon)', 2, 4.6, 12, 'available', '09:00:00', '17:00:00', 30, 18),
                (12, 'Dr. Dilani Wickramasinghe', 'Radiology', 'MBBS, MD (Consultant Radiologist)', 2, 4.3, 8, 'available', '08:00:00', '16:00:00', 30, 25),

                # Hemas Wattala (3)
                (13, 'Dr. Nuwan Senanayake', 'General Surgery', 'MBBS, MS (Consultant General Surgeon)', 3, 4.6, 17, 'available', '08:00:00', '17:00:00', 30, 20),
                (14, 'Dr. Priya Samarawickrama', 'Internal Medicine', 'MBBS, MD (Consultant Physician)', 3, 4.4, 7, 'available', '09:00:00', '16:00:00', 30, 20),
                (15, 'Dr. Lakshan Mendis', 'Orthopedics', 'MBBS, MS (Orthopedic Specialist)', 3, 4.5, 11, 'available', '08:30:00', '16:30:00', 30, 18),
                (16, 'Dr. Chandana Samarasinghe', 'Emergency Medicine', 'MBBS, MRCEM', 3, 4.5, 14, 'available', '00:00:00', '23:59:59', 20, 30),
                (17, 'Dr. Anura Liyanage', 'Radiology', 'MBBS, MD (Radiology)', 3, 4.2, 6, 'available', '08:00:00', '15:00:00', 30, 20),
                (18, 'Dr. Roshani de Silva', 'Pediatrics', 'MBBS, DCH (Pediatric Specialist)', 3, 4.4, 8, 'available', '09:00:00', '17:00:00', 30, 20),

                # Hemas Galle (4)
                (19, 'Dr. Rajan Krishnan', 'Cardiology', 'MBBS, MD, FRCP (Senior Cardiologist)', 4, 4.6, 22, 'available', '08:00:00', '17:00:00', 30, 20),
                (20, 'Dr. Kavitha Thayalan', 'Pediatrics', 'MBBS, MD (Consultant Pediatrician)', 4, 4.5, 14, 'available', '08:30:00', '16:30:00', 30, 22),
                (21, 'Dr. Murali Sivapalan', 'General Surgery', 'MBBS, MS, FRCS', 4, 4.4, 12, 'available', '09:00:00', '17:00:00', 30, 18),
                (22, 'Dr. Sumudu Perera', 'Internal Medicine', 'MBBS, MD (Consultant Physician)', 4, 4.3, 9, 'available', '08:00:00', '16:00:00', 30, 20),
                (23, 'Dr. Tharanga Madanayake', 'Orthopedics', 'MBBS, MS (Orthopedics)', 4, 4.2, 5, 'available', '09:00:00', '17:00:00', 30, 16),
                (24, 'Dr. Amara Wickrama', 'Neurology', 'MBBS, MD (Neurologist)', 4, 4.5, 9, 'available', '08:30:00', '16:30:00', 30, 18),

                # Hemas Kandy (5)
                (25, 'Dr. Buddhika Ratnasiri', 'General Surgery', 'MBBS, MS (General Surgeon)', 5, 4.5, 15, 'available', '08:00:00', '17:00:00', 30, 20),
                (26, 'Dr. Nayana Dissanayake', 'Emergency Medicine', 'MBBS, MRCEM', 5, 4.6, 12, 'available', '00:00:00', '23:59:59', 20, 30),
                (27, 'Dr. Malka Jayasinghe', 'Internal Medicine', 'MBBS, MD (Consultant Physician)', 5, 4.3, 10, 'available', '08:30:00', '16:30:00', 30, 20),
                (28, 'Dr. Prasad Gunawardena', 'Cardiology', 'MBBS, MD (Cardiologist)', 5, 4.4, 13, 'available', '08:00:00', '17:00:00', 30, 20),
                (29, 'Dr. Shivani Murugesan', 'Pediatrics', 'MBBS, MD (Pediatrics)', 5, 4.3, 14, 'available', '09:00:00', '16:30:00', 30, 20),
                (30, 'Dr. Prabhath Silva', 'Orthopedics', 'MBBS, MS (Orthopedics)', 5, 4.2, 11, 'available', '08:30:00', '17:00:00', 30, 18),

                # Hemas Kurunegala (6)
                (31, 'Dr. Dimuth Liyanage', 'Cardiology', 'MBBS, MD (Consultant Cardiologist)', 6, 4.5, 14, 'available', '08:00:00', '17:00:00', 30, 20),
                (32, 'Dr. Sunethra Perera', 'Emergency Medicine', 'MBBS, MD', 6, 4.6, 11, 'available', '00:00:00', '23:59:59', 20, 30),
                (33, 'Dr. Asela Gunaratne', 'General Surgery', 'MBBS, MS', 6, 4.4, 10, 'available', '09:00:00', '17:00:00', 30, 18),
                (34, 'Dr. Nadeeka Silva', 'Pediatrics', 'MBBS, DCH', 6, 4.3, 8, 'available', '08:30:00', '16:30:00', 30, 20),
                (35, 'Dr. Janaka Wickramasinghe', 'Internal Medicine', 'MBBS, MD', 6, 4.2, 9, 'available', '08:00:00', '16:00:00', 30, 20),
                (36, 'Dr. Chathura Bandara', 'Orthopedics', 'MBBS, MS', 6, 4.3, 7, 'available', '08:30:00', '16:30:00', 30, 18),
            ]
            for d in hemas_doctors:
                cursor.execute("""
                    INSERT INTO doctors (id, name, specialization, qualification, hospital_id, rating,
                                        experience_years, availability_status, working_start_time,
                                        working_end_time, consultation_duration_min, max_patients_per_day)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, d)

            hemas_resources = [
                # Hemas Colombo (1)
                ('icu_bed', 'ICU Bed', 'Intensive Care Unit', 1, 20, 7, 'available'),
                ('general_bed', 'General Ward Bed', 'General Ward', 1, 150, 55, 'available'),
                ('ventilator', 'Mechanical Ventilator', 'Critical Care', 1, 15, 6, 'available'),
                ('cardiac_unit', 'Cardiac Care Unit', 'Cardiology', 1, 10, 4, 'available'),
                ('ambulance', 'Emergency Ambulance', 'Emergency Logistics', 1, 5, 3, 'available'),
                ('room', 'Operating Theatre', 'Surgical Ward', 1, 6, 3, 'available'),
                ('equipment', 'MRI / CT Scanner', 'Radiology', 1, 3, 3, 'available'),
                ('blood_bank', 'Blood Bank Unit', 'Laboratory', 1, 1, 1, 'available'),

                # Hemas Thalawathugoda (2)
                ('icu_bed', 'ICU Bed', 'Intensive Care Unit', 2, 14, 5, 'available'),
                ('general_bed', 'General Ward Bed', 'General Ward', 2, 100, 38, 'available'),
                ('ventilator', 'Mechanical Ventilator', 'Critical Care', 2, 10, 4, 'available'),
                ('cardiac_unit', 'Cardiac Care Unit', 'Cardiology', 2, 6, 2, 'available'),
                ('ambulance', 'Emergency Ambulance', 'Emergency Logistics', 2, 4, 2, 'available'),
                ('room', 'Operating Theatre', 'Surgical Ward', 2, 4, 2, 'available'),
                ('equipment', 'MRI / CT Scanner', 'Radiology', 2, 2, 2, 'available'),

                # Hemas Wattala (3)
                ('icu_bed', 'ICU Bed', 'Intensive Care Unit', 3, 18, 6, 'available'),
                ('general_bed', 'General Ward Bed', 'General Ward', 3, 130, 45, 'available'),
                ('ventilator', 'Mechanical Ventilator', 'Critical Care', 3, 12, 5, 'available'),
                ('cardiac_unit', 'Cardiac Care Unit', 'Cardiology', 3, 8, 3, 'available'),
                ('ambulance', 'Emergency Ambulance', 'Emergency Logistics', 3, 4, 2, 'available'),
                ('room', 'Operating Theatre', 'Surgical Ward', 3, 4, 2, 'available'),
                ('blood_bank', 'Blood Bank Unit', 'Laboratory', 3, 1, 1, 'available'),

                # Hemas Galle (4)
                ('icu_bed', 'ICU Bed', 'Intensive Care Unit', 4, 10, 4, 'available'),
                ('general_bed', 'General Ward Bed', 'General Ward', 4, 80, 28, 'available'),
                ('ventilator', 'Mechanical Ventilator', 'Critical Care', 4, 8, 3, 'available'),
                ('ambulance', 'Emergency Ambulance', 'Emergency Logistics', 4, 3, 2, 'available'),
                ('room', 'Operating Theatre', 'Surgical Ward', 4, 3, 2, 'available'),
                ('blood_bank', 'Blood Bank Unit', 'Laboratory', 4, 1, 1, 'available'),

                # Hemas Kandy (5)
                ('icu_bed', 'ICU Bed', 'Intensive Care Unit', 5, 12, 4, 'available'),
                ('general_bed', 'General Ward Bed', 'General Ward', 5, 90, 32, 'available'),
                ('ventilator', 'Mechanical Ventilator', 'Critical Care', 5, 8, 3, 'available'),
                ('cardiac_unit', 'Cardiac Care Unit', 'Cardiology', 5, 4, 2, 'available'),
                ('ambulance', 'Emergency Ambulance', 'Emergency Logistics', 5, 3, 2, 'available'),
                ('room', 'Operating Theatre', 'Surgical Ward', 5, 3, 2, 'available'),

                # Hemas Kurunegala (6)
                ('icu_bed', 'ICU Bed', 'Intensive Care Unit', 6, 8, 3, 'available'),
                ('general_bed', 'General Ward Bed', 'General Ward', 6, 75, 25, 'available'),
                ('ventilator', 'Mechanical Ventilator', 'Critical Care', 6, 6, 2, 'available'),
                ('ambulance', 'Emergency Ambulance', 'Emergency Logistics', 6, 3, 1, 'available'),
                ('room', 'Operating Theatre', 'Surgical Ward', 6, 3, 2, 'available'),
                ('equipment', 'Digital X-Ray', 'Radiology', 6, 2, 2, 'available'),
            ]
            for r in hemas_resources:
                cursor.execute("""
                    INSERT INTO resources (resource_type, resource_name, department, hospital_id,
                                          quantity, available_quantity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, r)

            cursor.execute("UPDATE appointments SET hospital_id = ((id % 6) + 1), doctor_id = ((id % 36) + 1) WHERE hospital_id > 6 OR doctor_id > 36")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            db.commit()
    except Exception as e:
        logger.error("Error setting up Hemas hospitals: %s", e)


# ════════════════════════════════════════════════════════════════
# HOSPITALS
# ════════════════════════════════════════════════════════════════

@hospital_bp.route('/hospitals')
@login_required
def list_hospitals():
    _ensure_hemas_hospitals()
    hospitals = query_db("""
        SELECT h.id, h.name, h.location_id, l.name AS city, h.address,
               h.capacity, h.available_beds, h.icu_beds, h.available_icu_beds,
               h.rating, h.status, h.opening_time, h.closing_time, h.avg_wait_time_min,
               (SELECT COUNT(*) FROM doctors d WHERE d.hospital_id = h.id) AS doctor_count
        FROM hospitals h
        JOIN locations l ON h.location_id = l.id
        ORDER BY h.name
    """) or []
    return render_template('hospitals/list.html', hospitals=hospitals)


@hospital_bp.route('/hospitals/add', methods=['GET'])
@role_required('admin')
def add_hospital_form():
    locations = query_db("SELECT id, name FROM locations ORDER BY name") or []
    return render_template('hospitals/form.html', h=None, locations=locations, mode='add')


@hospital_bp.route('/hospitals/add', methods=['POST'])
@role_required('admin')
def add_hospital():
    try:
        query_db("""
            INSERT INTO hospitals (name, location_id, address, capacity, available_beds,
                icu_beds, available_icu_beds, rating, status, opening_time, closing_time, avg_wait_time_min)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['location_id'],
            request.form.get('address', ''),
            request.form.get('capacity', 100),
            request.form.get('available_beds', 50),
            request.form.get('icu_beds', 10),
            request.form.get('available_icu_beds', 5),
            request.form.get('rating', 4.0),
            request.form.get('status', 'active'),
            request.form.get('opening_time', '08:00:00'),
            request.form.get('closing_time', '20:00:00'),
            request.form.get('avg_wait_time_min', 30),
        ))
        flash(f'Hospital "{request.form["name"]}" added.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('hospital.list_hospitals'))


@hospital_bp.route('/hospitals/<int:hid>/edit', methods=['GET'])
@role_required('admin', 'operator')
def edit_hospital_form(hid):
    h = query_db("SELECT * FROM hospitals WHERE id=%s", (hid,), one=True)
    if not h:
        flash('Hospital not found.', 'danger')
        return redirect(url_for('hospital.list_hospitals'))
    locations = query_db("SELECT id, name FROM locations ORDER BY name") or []
    return render_template('hospitals/form.html', h=h, locations=locations, mode='edit')


@hospital_bp.route('/hospitals/<int:hid>/edit', methods=['POST'])
@role_required('admin', 'operator')
def edit_hospital(hid):
    try:
        query_db("""
            UPDATE hospitals SET name=%s, location_id=%s, address=%s, capacity=%s,
            available_beds=%s, icu_beds=%s, available_icu_beds=%s,
            rating=%s, status=%s, opening_time=%s, closing_time=%s, avg_wait_time_min=%s WHERE id=%s
        """, (
            request.form['name'],
            request.form['location_id'],
            request.form.get('address', ''),
            request.form.get('capacity', 100),
            request.form.get('available_beds', 50),
            request.form.get('icu_beds', 10),
            request.form.get('available_icu_beds', 5),
            request.form.get('rating', 4.0),
            request.form.get('status', 'active'),
            request.form.get('opening_time', '08:00:00'),
            request.form.get('closing_time', '20:00:00'),
            request.form.get('avg_wait_time_min', 30),
            hid,
        ))
        flash(f'Hospital updated successfully.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('hospital.list_hospitals'))


@hospital_bp.route('/hospitals/<int:hid>/delete', methods=['POST'])
@role_required('admin')
def delete_hospital(hid):
    h = query_db("SELECT name FROM hospitals WHERE id=%s", (hid,), one=True)
    if h:
        try:
            query_db("DELETE FROM hospitals WHERE id=%s", (hid,))
            flash(f'Hospital "{h["name"]}" deleted.', 'success')
        except Exception as e:
            flash(f'Cannot delete: {e}', 'danger')
    return redirect(url_for('hospital.list_hospitals'))


# ════════════════════════════════════════════════════════════════
# DOCTORS
# ════════════════════════════════════════════════════════════════

@hospital_bp.route('/doctors')
@login_required
def list_doctors():
    _ensure_hemas_hospitals()
    doctors = query_db("""
        SELECT d.id, d.name, d.specialization, d.qualification, d.rating, d.experience_years,
               d.availability_status, d.working_start_time, d.working_end_time,
               d.consultation_duration_min, d.max_patients_per_day, d.current_patients_today,
               h.name AS hospital_name, d.hospital_id
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY d.name
    """) or []
    return render_template('doctors/list.html', doctors=doctors)


@hospital_bp.route('/doctors/<int:did>')
@hospital_bp.route('/doctors/<int:did>/details')
@login_required
def doctor_details(did):
    """View comprehensive doctor details including assigned patient list, hospital, and schedules."""
    doctor = query_db("""
        SELECT d.*, h.name AS hospital_name, h.address AS hospital_address
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        WHERE d.id = %s
    """, (did,), one=True)

    if not doctor:
        flash('Doctor not found.', 'danger')
        return redirect(url_for('hospital.list_doctors'))

    # Patients assigned to this doctor
    assigned_patients = query_db("""
        SELECT a.id AS appointment_id, a.appointment_date, a.start_time, a.end_time,
               a.status, a.room_number, a.notes,
               p.id AS patient_id, p.name AS patient_name, p.age, p.gender,
               p.blood_type, p.phone, p.emergency_level
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date DESC, a.start_time ASC
    """, (did,)) or []

    return render_template(
        'doctors/view.html',
        doctor=doctor,
        assigned_patients=assigned_patients
    )



@hospital_bp.route('/doctors/add', methods=['GET'])
@role_required('admin')
def add_doctor_form():
    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []
    specs = ['Cardiology','Neurology','Orthopedics','Pediatrics','Emergency Medicine',
             'General Surgery','Internal Medicine','Obstetrics and Gynecology','Radiology']
    return render_template('doctors/form.html', d=None, hospitals=hospitals,
                           specs=specs, mode='add')


@hospital_bp.route('/doctors/add', methods=['POST'])
@role_required('admin')
def add_doctor():
    try:
        query_db("""
            INSERT INTO doctors (name, specialization, qualification, hospital_id, rating,
                experience_years, availability_status, working_start_time, working_end_time,
                consultation_duration_min, max_patients_per_day)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['specialization'],
            request.form.get('qualification', 'Consultant Specialist'),
            request.form['hospital_id'],
            request.form.get('rating', 4.0),
            request.form.get('experience_years', 5),
            request.form.get('availability_status', 'available'),
            request.form.get('working_start_time', '09:00:00'),
            request.form.get('working_end_time', '17:00:00'),
            request.form.get('consultation_duration_min', 30),
            request.form.get('max_patients_per_day', 20),
        ))
        flash(f'Dr. {request.form["name"]} added.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('hospital.list_doctors'))


@hospital_bp.route('/doctors/<int:did>/edit', methods=['GET'])
@role_required('admin', 'operator')
def edit_doctor_form(did):
    d = query_db("SELECT * FROM doctors WHERE id=%s", (did,), one=True)
    if not d:
        flash('Doctor not found.', 'danger')
        return redirect(url_for('hospital.list_doctors'))
    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []
    specs = ['Cardiology','Neurology','Orthopedics','Pediatrics','Emergency Medicine',
             'General Surgery','Internal Medicine','Obstetrics and Gynecology','Radiology']
    return render_template('doctors/form.html', d=d, hospitals=hospitals,
                           specs=specs, mode='edit')


@hospital_bp.route('/doctors/<int:did>/edit', methods=['POST'])
@role_required('admin', 'operator')
def edit_doctor(did):
    try:
        query_db("""
            UPDATE doctors SET name=%s, specialization=%s, qualification=%s, hospital_id=%s,
            rating=%s, experience_years=%s, availability_status=%s, working_start_time=%s,
            working_end_time=%s, consultation_duration_min=%s, max_patients_per_day=%s WHERE id=%s
        """, (
            request.form['name'],
            request.form['specialization'],
            request.form.get('qualification', 'Consultant Specialist'),
            request.form['hospital_id'],
            request.form.get('rating', 4.0),
            request.form.get('experience_years', 5),
            request.form.get('availability_status', 'available'),
            request.form.get('working_start_time', '09:00:00'),
            request.form.get('working_end_time', '17:00:00'),
            request.form.get('consultation_duration_min', 30),
            request.form.get('max_patients_per_day', 20),
            did,
        ))
        flash('Doctor updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('hospital.list_doctors'))


@hospital_bp.route('/doctors/<int:did>/delete', methods=['POST'])
@role_required('admin')
def delete_doctor(did):
    d = query_db("SELECT name FROM doctors WHERE id=%s", (did,), one=True)
    if d:
        try:
            query_db("DELETE FROM doctors WHERE id=%s", (did,))
            flash(f'Dr. {d["name"]} deleted.', 'success')
        except Exception as e:
            flash(f'Cannot delete: {e}', 'danger')
    return redirect(url_for('hospital.list_doctors'))


# ════════════════════════════════════════════════════════════════
# RESOURCES
# ════════════════════════════════════════════════════════════════

@hospital_bp.route('/resources')
@login_required
def list_resources():
    resources = query_db("""
        SELECT r.id, r.resource_type, r.resource_name, r.department, r.quantity,
               r.available_quantity, r.status, h.name AS hospital_name, r.hospital_id
        FROM resources r
        JOIN hospitals h ON r.hospital_id = h.id
        ORDER BY h.name, r.resource_type
    """) or []
    return render_template('resources/list.html', resources=resources)


@hospital_bp.route('/resources/add', methods=['GET'])
@role_required('admin')
def add_resource_form():
    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []
    return render_template('resources/form.html', r=None, hospitals=hospitals, mode='add')


@hospital_bp.route('/resources/add', methods=['POST'])
@role_required('admin')
def add_resource():
    try:
        query_db("""
            INSERT INTO resources (resource_type, resource_name, department, hospital_id,
                quantity, available_quantity, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['resource_type'],
            request.form['resource_name'],
            request.form.get('department', 'General'),
            request.form['hospital_id'],
            request.form.get('quantity', 1),
            request.form.get('available_quantity', 1),
            request.form.get('status', 'available'),
        ))
        flash('Resource added.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('hospital.list_resources'))


@hospital_bp.route('/resources/<int:rid>/edit', methods=['GET'])
@role_required('admin', 'operator')
def edit_resource_form(rid):
    r = query_db("SELECT * FROM resources WHERE id=%s", (rid,), one=True)
    if not r:
        flash('Resource not found.', 'danger')
        return redirect(url_for('hospital.list_resources'))
    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []
    return render_template('resources/form.html', r=r, hospitals=hospitals, mode='edit')


@hospital_bp.route('/resources/<int:rid>/edit', methods=['POST'])
@role_required('admin', 'operator')
def edit_resource(rid):
    try:
        query_db("""
            UPDATE resources SET resource_type=%s, resource_name=%s, department=%s, hospital_id=%s,
            quantity=%s, available_quantity=%s, status=%s WHERE id=%s
        """, (
            request.form['resource_type'],
            request.form['resource_name'],
            request.form.get('department', 'General'),
            request.form['hospital_id'],
            request.form.get('quantity', 1),
            request.form.get('available_quantity', 1),
            request.form.get('status', 'available'),
            rid,
        ))
        flash('Resource updated.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('hospital.list_resources'))


@hospital_bp.route('/resources/<int:rid>/delete', methods=['POST'])
@role_required('admin')
def delete_resource(rid):
    r = query_db("SELECT resource_name FROM resources WHERE id=%s", (rid,), one=True)
    if r:
        try:
            query_db("DELETE FROM resources WHERE id=%s", (rid,))
            flash(f'Resource "{r["resource_name"]}" deleted.', 'success')
        except Exception as e:
            flash(f'Cannot delete: {e}', 'danger')
    return redirect(url_for('hospital.list_resources'))


# ════════════════════════════════════════════════════════════════
# APPOINTMENT HISTORY
# ════════════════════════════════════════════════════════════════

@hospital_bp.route('/appointments')
@login_required
def appointment_history():
    """Comprehensive Appointment History & Consultation Log."""
    date_filter = request.args.get('date', '').strip()
    search_q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip().lower()
    hospital_filter = request.args.get('hospital_id', type=int)

    base_sql = """
        SELECT a.id, a.patient_id, a.doctor_id, a.hospital_id,
               a.room_number, a.appointment_date, a.start_time, a.end_time,
               a.duration_min, a.status, a.notes, a.created_at,
               p.name AS patient_name, p.phone AS patient_phone, p.age AS patient_age,
               d.name AS doctor_name, d.specialization AS doctor_specialization,
               h.name AS hospital_name, l.name AS hospital_city
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        JOIN hospitals h ON a.hospital_id = h.id
        LEFT JOIN locations l ON h.location_id = l.id
        WHERE 1=1
    """
    params = []

    # 1. Date Filter (supports HTML date picker YYYY-MM-DD or standard formats)
    parsed_date_str = None
    if date_filter:
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d'):
            try:
                parsed_date_str = datetime.strptime(date_filter, fmt).strftime('%Y-%m-%d')
                break
            except Exception:
                pass
        if parsed_date_str:
            base_sql += " AND DATE(a.appointment_date) = %s"
            params.append(parsed_date_str)
        else:
            base_sql += " AND (DATE(a.appointment_date) = %s OR CAST(a.appointment_date AS CHAR) LIKE %s)"
            params.extend([date_filter, f"%{date_filter}%"])

    # 2. Name Search (Patient name or Doctor name - flexible multi-token matching)
    if search_q:
        q_clean = search_q.strip().lower()
        tokens = [t for t in q_clean.split() if t]
        if tokens:
            name_parts = []
            for t in tokens:
                name_parts.append("(LOWER(p.name) LIKE %s OR LOWER(d.name) LIKE %s)")
                params.extend([f"%{t}%", f"%{t}%"])
            base_sql += f" AND ({' OR '.join(name_parts)})"
        else:
            base_sql += " AND (LOWER(p.name) LIKE %s OR LOWER(d.name) LIKE %s)"
            params.extend([f"%{q_clean}%", f"%{q_clean}%"])

    if status_filter:
        base_sql += " AND a.status = %s"
        params.append(status_filter)
    if hospital_filter:
        base_sql += " AND a.hospital_id = %s"
        params.append(hospital_filter)

    # Auto-sync appointments from emergency_requests if missing
    try:
        unlinked_ers = query_db("""
            SELECT er.id, er.patient_id, er.recommended_hospital_id, er.preferred_date, er.preferred_time_slot,
                   er.required_specialization, er.status, er.created_at
            FROM emergency_requests er
            WHERE er.patient_id NOT IN (SELECT DISTINCT patient_id FROM appointments)
        """) or []
        for er in unlinked_ers:
            hid = er.get('recommended_hospital_id') or 1
            doc_row = query_db("SELECT id FROM doctors WHERE hospital_id = %s LIMIT 1", (hid,), one=True)
            did = doc_row['id'] if doc_row else 1
            appt_date = er.get('preferred_date') or str(er.get('created_at', ''))[:10] or datetime.now().strftime('%Y-%m-%d')
            start_t = '14:00:00' if er.get('preferred_time_slot') == 'afternoon' else ('17:00:00' if er.get('preferred_time_slot') == 'evening' else '09:00:00')
            end_t = '14:30:00' if er.get('preferred_time_slot') == 'afternoon' else ('17:30:00' if er.get('preferred_time_slot') == 'evening' else '09:30:00')
            execute_db("""
                INSERT INTO appointments (
                    patient_id, doctor_id, hospital_id, room_number, appointment_date,
                    start_time, end_time, duration_min, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                er['patient_id'], did, hid, f"Room {(er['patient_id'] % 20) + 1:02d}",
                appt_date, start_t, end_t, 30, 'scheduled',
                f"Emergency Care Plan #{er['id']} - {er.get('required_specialization') or 'General'}"
            ))
    except Exception as ex:
        logger.error("Sync error: %s", ex)

    base_sql += " ORDER BY a.appointment_date DESC, a.start_time DESC"
    appointments = query_db(base_sql, tuple(params)) or []

    # If 0 results were found when searching by both Date and Name, check if appointments exist for that Name on other dates
    other_date_appointments = []
    registered_patient_without_appt = None

    if len(appointments) == 0 and search_q:
        q_clean = search_q.strip().lower()
        if date_filter:
            fallback_sql = """
                SELECT a.id, a.patient_id, a.doctor_id, a.hospital_id,
                       a.room_number, a.appointment_date, a.start_time, a.end_time,
                       a.duration_min, a.status, a.notes, a.created_at,
                       p.name AS patient_name, p.phone AS patient_phone, p.age AS patient_age,
                       d.name AS doctor_name, d.specialization AS doctor_specialization,
                       h.name AS hospital_name, l.name AS hospital_city
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                JOIN hospitals h ON a.hospital_id = h.id
                LEFT JOIN locations l ON h.location_id = l.id
                WHERE (LOWER(p.name) LIKE %s OR LOWER(d.name) LIKE %s)
                ORDER BY a.appointment_date DESC, a.start_time DESC
            """
            other_date_appointments = query_db(fallback_sql, (f"%{q_clean}%", f"%{q_clean}%")) or []
        
        # Also check if patient is registered in the system but has no appointments at all
        if not other_date_appointments:
            matched_patient = query_db("""
                SELECT p.id, p.name, p.phone, p.age, p.gender, p.emergency_level, p.required_specialization,
                       l.name AS location_name
                FROM patients p
                LEFT JOIN locations l ON p.location_id = l.id
                WHERE LOWER(p.name) LIKE %s
                LIMIT 1
            """, (f"%{q_clean}%",), one=True)
            if matched_patient:
                registered_patient_without_appt = matched_patient

    # KPI counts
    stats = {
        'total': (query_db("SELECT COUNT(*) AS c FROM appointments", one=True) or {}).get('c', 0),
        'scheduled': (query_db("SELECT COUNT(*) AS c FROM appointments WHERE status='scheduled'", one=True) or {}).get('c', 0),
        'completed': (query_db("SELECT COUNT(*) AS c FROM appointments WHERE status='completed'", one=True) or {}).get('c', 0),
        'cancelled': (query_db("SELECT COUNT(*) AS c FROM appointments WHERE status='cancelled'", one=True) or {}).get('c', 0),
    }

    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []

    return render_template(
        'appointments/history.html',
        appointments=appointments,
        other_date_appointments=other_date_appointments,
        registered_patient_without_appt=registered_patient_without_appt,
        stats=stats,
        hospitals=hospitals,
        status_filter=status_filter,
        hospital_filter=hospital_filter,
        date_filter=date_filter,
        search_q=search_q,
    )


@hospital_bp.route('/appointments/<int:aid>/status', methods=['POST'])
@login_required
def update_appointment_status(aid: int):
    """Update status of an appointment (scheduled, completed, cancelled)."""
    new_status = request.form.get('status', '').strip().lower()
    if new_status in ['scheduled', 'completed', 'cancelled', 'pending']:
        query_db("UPDATE appointments SET status = %s WHERE id = %s", (new_status, aid))
        flash(f'Appointment #{aid} status updated to {new_status.title()}.', 'success')
    return redirect(request.referrer or url_for('hospital.appointment_history'))
