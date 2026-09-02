"""
routes/report_routes.py
=======================
Admin Reports & Analytics module:
  - Stock Reports (Hospital Beds, ICU, Equipment, Ambulances, Resources inventory)
  - Daily Operations Reports (Emergencies, Appointments, Doctor Consultations, Algorithms)
  - Export to CSV & Print Views
"""

import io
import csv
from datetime import datetime, date
import logging
from flask import (
    Blueprint, render_template, request, Response, session,
    redirect, url_for, flash
)

from routes.auth_routes import login_required, role_required
from database.db import query_db

logger = logging.getLogger(__name__)

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


# ════════════════════════════════════════════════════════════════
# 1. REPORTS HUB / OVERVIEW
# ════════════════════════════════════════════════════════════════
@reports_bp.route('/')
@role_required('admin')
def index():
    """Main Reports & Analytics Hub dashboard."""
    today = date.today().strftime('%Y-%m-%d')

    # Summary metrics for quick overview cards
    hospital_stats = query_db("""
        SELECT 
            COUNT(id) AS total_hospitals,
            SUM(capacity) AS total_capacity,
            SUM(available_beds) AS total_available_beds,
            SUM(icu_beds) AS total_icu_beds,
            SUM(available_icu_beds) AS total_available_icu
        FROM hospitals
    """, one=True) or {}

    resource_stats = query_db("""
        SELECT 
            COUNT(id) AS total_resource_items,
            SUM(quantity) AS total_quantity,
            SUM(available_quantity) AS total_available,
            SUM(CASE WHEN status = 'unavailable' OR available_quantity = 0 THEN 1 ELSE 0 END) AS depleted_items
        FROM resources
    """, one=True) or {}

    daily_ops = query_db("""
        SELECT 
            (SELECT COUNT(*) FROM emergency_requests WHERE DATE(created_at) = %s) AS emergencies_today,
            (SELECT COUNT(*) FROM appointments WHERE appointment_date = %s) AS appointments_today,
            (SELECT COUNT(*) FROM appointments WHERE appointment_date = %s AND status = 'completed') AS completed_today,
            (SELECT COUNT(*) FROM algorithm_results WHERE DATE(created_at) = %s) AS algo_runs_today
    """, (today, today, today, today), one=True) or {}

    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []

    return render_template(
        'reports/index.html',
        hospital_stats=hospital_stats,
        resource_stats=resource_stats,
        daily_ops=daily_ops,
        hospitals=hospitals,
        today=today,
    )


# ════════════════════════════════════════════════════════════════
# 2. STOCK & INVENTORY REPORT
# ════════════════════════════════════════════════════════════════
@reports_bp.route('/stock')
@role_required('admin')
def stock_report():
    """Comprehensive hospital beds, ICU capacity, and specialized equipment stock report."""
    selected_hospital_id = request.args.get('hospital_id', type=int)
    selected_resource_type = request.args.get('resource_type', '').strip()
    status_filter = request.args.get('status', '').strip()

    # Base query for hospital bed & ICU capacity stock
    hosp_sql = """
        SELECT h.id, h.name, l.name AS city, h.address,
               h.capacity, h.available_beds,
               (h.capacity - h.available_beds) AS occupied_beds,
               ROUND(((h.capacity - h.available_beds) / NULLIF(h.capacity, 0)) * 100, 1) AS bed_occupancy_rate,
               h.icu_beds, h.available_icu_beds,
               (h.icu_beds - h.available_icu_beds) AS occupied_icu_beds,
               ROUND(((h.icu_beds - h.available_icu_beds) / NULLIF(h.icu_beds, 0)) * 100, 1) AS icu_occupancy_rate,
               h.status, h.rating
        FROM hospitals h
        JOIN locations l ON h.location_id = l.id
    """
    hosp_params = []
    if selected_hospital_id:
        hosp_sql += " WHERE h.id = %s"
        hosp_params.append(selected_hospital_id)
    hosp_sql += " ORDER BY h.name"
    hospital_stocks = query_db(hosp_sql, tuple(hosp_params)) or []

    # Detailed medical resources and equipment stock
    res_sql = """
        SELECT r.id, r.hospital_id, h.name AS hospital_name,
               r.resource_type, r.resource_name, r.department,
               r.quantity, r.available_quantity,
               (r.quantity - r.available_quantity) AS in_use_quantity,
               ROUND((r.available_quantity / NULLIF(r.quantity, 0)) * 100, 1) AS availability_pct,
               r.status
        FROM resources r
        JOIN hospitals h ON r.hospital_id = h.id
        WHERE 1=1
    """
    res_params = []
    if selected_hospital_id:
        res_sql += " AND r.hospital_id = %s"
        res_params.append(selected_hospital_id)
    if selected_resource_type:
        res_sql += " AND r.resource_type = %s"
        res_params.append(selected_resource_type)
    if status_filter:
        res_sql += " AND r.status = %s"
        res_params.append(status_filter)
    res_sql += " ORDER BY h.name, r.department, r.resource_name"
    resource_items = query_db(res_sql, tuple(res_params)) or []

    # Aggregate summaries
    total_capacity = sum(h['capacity'] for h in hospital_stocks)
    total_avail_beds = sum(h['available_beds'] for h in hospital_stocks)
    total_icu = sum(h['icu_beds'] for h in hospital_stocks)
    total_avail_icu = sum(h['available_icu_beds'] for h in hospital_stocks)

    total_equipment_qty = sum(r['quantity'] for r in resource_items)
    total_equipment_avail = sum(r['available_quantity'] for r in resource_items)

    # Dropdown lists for filter options
    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []
    resource_types = query_db("SELECT DISTINCT resource_type FROM resources ORDER BY resource_type") or []

    return render_template(
        'reports/stock_report.html',
        hospital_stocks=hospital_stocks,
        resource_items=resource_items,
        hospitals=hospitals,
        resource_types=resource_types,
        selected_hospital_id=selected_hospital_id,
        selected_resource_type=selected_resource_type,
        status_filter=status_filter,
        summary={
            'total_capacity': total_capacity,
            'total_avail_beds': total_avail_beds,
            'bed_occupancy_pct': round(((total_capacity - total_avail_beds) / max(total_capacity, 1)) * 100, 1),
            'total_icu': total_icu,
            'total_avail_icu': total_avail_icu,
            'icu_occupancy_pct': round(((total_icu - total_avail_icu) / max(total_icu, 1)) * 100, 1),
            'total_equipment_qty': total_equipment_qty,
            'total_equipment_avail': total_equipment_avail,
        },
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )


# ════════════════════════════════════════════════════════════════
# 3. DAILY OPERATIONS REPORT
# ════════════════════════════════════════════════════════════════
@reports_bp.route('/daily')
@role_required('admin')
def daily_report():
    """Comprehensive daily operations report: Emergencies, Appointments, Doctors & DSS Runs."""
    report_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))

    # Validate date
    try:
        parsed_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today().strftime('%Y-%m-%d')
        parsed_date = date.today()

    # 1. Emergency Requests on this date
    emergencies = query_db("""
        SELECT er.id, er.emergency_level, er.required_specialization,
               er.status, er.created_at,
               p.name AS patient_name, p.age AS patient_age, p.blood_type,
               l.name AS location_name, h.name AS hospital_name
        FROM emergency_requests er
        JOIN patients p ON er.patient_id = p.id
        LEFT JOIN locations l ON er.source_location_id = l.id
        LEFT JOIN hospitals h ON er.recommended_hospital_id = h.id
        WHERE DATE(er.created_at) = %s
        ORDER BY er.created_at DESC
    """, (report_date,)) or []

    # Emergency breakdown
    emergency_by_level = {
        'critical': sum(1 for e in emergencies if e['emergency_level'] == 'critical'),
        'high': sum(1 for e in emergencies if e['emergency_level'] == 'high'),
        'medium': sum(1 for e in emergencies if e['emergency_level'] == 'medium'),
        'low': sum(1 for e in emergencies if e['emergency_level'] == 'low'),
    }

    # 2. Appointments on this date
    appointments = query_db("""
        SELECT a.id, a.start_time, a.end_time, a.duration_min, a.status, a.room_number, a.notes,
               p.name AS patient_name, p.phone AS patient_phone,
               d.name AS doctor_name, d.specialization,
               h.name AS hospital_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        JOIN hospitals h ON a.hospital_id = h.id
        WHERE a.appointment_date = %s
        ORDER BY a.start_time ASC, h.name ASC
    """, (report_date,)) or []

    # Appointment status counts
    appt_status_counts = {
        'scheduled': sum(1 for a in appointments if a['status'] == 'scheduled'),
        'completed': sum(1 for a in appointments if a['status'] == 'completed'),
        'cancelled': sum(1 for a in appointments if a['status'] == 'cancelled'),
        'pending': sum(1 for a in appointments if a['status'] == 'pending'),
    }

    # 3. Doctor Daily Workload on this date
    doctors_workload = query_db("""
        SELECT d.id, d.name, d.specialization, d.availability_status,
               d.working_start_time, d.working_end_time, d.max_patients_per_day,
               h.name AS hospital_name,
               (SELECT COUNT(*) FROM appointments a 
                WHERE a.doctor_id = d.id AND a.appointment_date = %s) AS booked_appointments,
               (SELECT COUNT(*) FROM appointments a 
                WHERE a.doctor_id = d.id AND a.appointment_date = %s AND a.status = 'completed') AS completed_appointments
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY booked_appointments DESC, d.name ASC
    """, (report_date, report_date)) or []

    # 4. Algorithm Optimization Performance on this date
    algo_runs = query_db("""
        SELECT module, algorithm, input_size, execution_time_ms, memory_kb,
               solution_quality, created_at
        FROM algorithm_results
        WHERE DATE(created_at) = %s
        ORDER BY created_at DESC
    """, (report_date,)) or []

    avg_exec_time = round(sum(float(a['execution_time_ms'] or 0) for a in algo_runs) / max(len(algo_runs), 1), 3)

    return render_template(
        'reports/daily_report.html',
        report_date=report_date,
        emergencies=emergencies,
        emergency_by_level=emergency_by_level,
        appointments=appointments,
        appt_status_counts=appt_status_counts,
        doctors_workload=doctors_workload,
        algo_runs=algo_runs,
        avg_exec_time=avg_exec_time,
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )


# ════════════════════════════════════════════════════════════════
# 4. EXPORT TO CSV
# ════════════════════════════════════════════════════════════════
@reports_bp.route('/export/<report_type>')
@role_required('admin')
def export_csv(report_type):
    """Export Stock or Daily Reports data into a downloadable CSV file."""
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'stock':
        writer.writerow(['Hospital Name', 'City', 'Total Capacity', 'Available Beds', 'Occupied Beds',
                         'Bed Occupancy (%)', 'Total ICU Beds', 'Available ICU', 'ICU Occupancy (%)', 'Status'])
        hospitals = query_db("""
            SELECT h.name, l.name AS city, h.capacity, h.available_beds,
                   (h.capacity - h.available_beds) AS occ_beds,
                   ROUND(((h.capacity - h.available_beds) / NULLIF(h.capacity, 0)) * 100, 1) AS bed_rate,
                   h.icu_beds, h.available_icu_beds,
                   (h.icu_beds - h.available_icu_beds) AS occ_icu,
                   ROUND(((h.icu_beds - h.available_icu_beds) / NULLIF(h.icu_beds, 0)) * 100, 1) AS icu_rate,
                   h.status
            FROM hospitals h
            JOIN locations l ON h.location_id = l.id
            ORDER BY h.name
        """) or []
        for h in hospitals:
            writer.writerow([
                h['name'], h['city'], h['capacity'], h['available_beds'], h['occ_beds'],
                f"{h['bed_rate']}%", h['icu_beds'], h['available_icu_beds'], h['occ_icu'],
                f"{h['icu_rate']}%", h['status']
            ])

        writer.writerow([])
        writer.writerow(['Hospital', 'Department', 'Resource Name', 'Resource Type', 'Total Quantity', 'Available Quantity', 'Status'])
        resources = query_db("""
            SELECT h.name AS hospital_name, r.department, r.resource_name, r.resource_type,
                   r.quantity, r.available_quantity, r.status
            FROM resources r
            JOIN hospitals h ON r.hospital_id = h.id
            ORDER BY h.name, r.department, r.resource_name
        """) or []
        for r in resources:
            writer.writerow([
                r['hospital_name'], r['department'], r['resource_name'], r['resource_type'],
                r['quantity'], r['available_quantity'], r['status']
            ])

        filename = f"mediroute_stock_report_{date.today().strftime('%Y%m%d')}.csv"

    elif report_type == 'daily':
        report_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        writer.writerow([f'MediRoute Daily Operations Report - {report_date}'])
        writer.writerow([])
        writer.writerow(['--- EMERGENCIES ---'])
        writer.writerow(['ID', 'Patient', 'Urgency', 'Specialist', 'Hospital', 'Status', 'Time'])
        emergencies = query_db("""
            SELECT er.id, p.name AS patient_name, er.emergency_level, er.required_specialization,
                   h.name AS hospital_name, er.status, er.created_at
            FROM emergency_requests er
            JOIN patients p ON er.patient_id = p.id
            LEFT JOIN hospitals h ON er.recommended_hospital_id = h.id
            WHERE DATE(er.created_at) = %s
            ORDER BY er.created_at DESC
        """, (report_date,)) or []
        for e in emergencies:
            writer.writerow([e['id'], e['patient_name'], e['emergency_level'], e['required_specialization'],
                             e['hospital_name'] or 'N/A', e['status'], e['created_at']])

        writer.writerow([])
        writer.writerow(['--- APPOINTMENTS ---'])
        writer.writerow(['ID', 'Patient', 'Doctor', 'Hospital', 'Start Time', 'Duration (min)', 'Status'])
        appointments = query_db("""
            SELECT a.id, p.name AS patient_name, d.name AS doctor_name, h.name AS hospital_name,
                   a.start_time, a.duration_min, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            JOIN hospitals h ON a.hospital_id = h.id
            WHERE a.appointment_date = %s
            ORDER BY a.start_time ASC
        """, (report_date,)) or []
        for a in appointments:
            writer.writerow([a['id'], a['patient_name'], a['doctor_name'], a['hospital_name'],
                             a['start_time'], a['duration_min'], a['status']])

        filename = f"mediroute_daily_report_{report_date.replace('-', '')}.csv"
    else:
        return "Invalid report type", 400

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
