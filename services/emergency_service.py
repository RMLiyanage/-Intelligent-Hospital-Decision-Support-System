"""
services/emergency_service.py
==============================
Core Orchestration Service for MediRoute.

Executes the complete 7-step real-world Intelligent Hospital Decision Support
pipeline as requested by the user:

  1. Patient Request: Capture emergency requirements (location, level, specialization).
  2. Task 4 (Intelligent Decision): Recommend best hospital/doctor via Weighted Ranking (MCDA).
  3. Task 2 (Resource Allocation): Verify and allocate required beds/equipment via Greedy Allocation.
  4. Task 3 (Network Analysis): Check department connectivity (BFS/DFS) & facility matrix (Floyd-Warshall).
  5. Task 1 (Route Optimization): Identify closest available ambulance & compute optimal A* route.
  6. Supporting Feature: Book and confirm ambulance reservation with mock payment reference.
  7. Task 5 (Optimization & Scheduling): Schedule follow-up consultation using Genetic Algorithm.

All results are compiled into a master JSON payload and saved to `emergency_requests`.
"""

import json
import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from database.db import execute_db, query_db
from data_structures.patient import Patient
from data_structures.hospital import Hospital
from data_structures.appointment import Appointment
from data_structures.doctor import Doctor

from services.decision_service import recommend_hospital
from services.allocation_service import run_resource_allocation
from services.network_service import run_network_analysis
from services.route_service import find_optimal_route, find_closest_suitable_hospital
from services.scheduling_service import optimize_schedule
from services.performance_service import log_algorithm_result

logger = logging.getLogger(__name__)


def process_emergency_pipeline(
    patient_id: int,
    emergency_level: str = 'critical',
    required_specialization: Optional[str] = None,
    source_location_id: Optional[int] = None,
    preferred_date: Optional[str] = None,
    preferred_time_slot: str = 'morning',
    created_by_user_id: Optional[int] = None,
    require_ambulance: bool = True,
) -> Dict[str, Any]:
    """
    Orchestrate the complete 7-step IDSS pipeline.

    Returns
    -------
    dict : Master pipeline execution result containing outputs from all 5 modules.
    """
    pipeline_start = datetime.now()
    session_id = str(uuid.uuid4())

    # Fetch patient details
    p_row = query_db(
        "SELECT id, name, age, gender, emergency_level, location_id, blood_type, required_specialization "
        "FROM patients WHERE id = %s",
        (patient_id,),
        one=True,
    )
    if not p_row:
        raise ValueError(f"Patient {patient_id} not found")

    patient = Patient.from_db_row(p_row)
    if emergency_level:
        patient.emergency_level = emergency_level
    if required_specialization:
        patient.required_specialization = required_specialization
    if source_location_id:
        patient.location_id = source_location_id

    source_loc_id = patient.location_id or 1  # Default to Colombo Fort if null

    # ------------------------------------------------------------------------
    # STEP 1: Task 1 – Route Optimization (Multi-Target: Filter + Shortest-Path)
    # ------------------------------------------------------------------------
    # Following Chapter 3 §3.2 & §3.5:
    #   1. Filter hospital branches by the patient's required specialization.
    #   2. Run A* from the patient location to EACH eligible branch.
    #   3. Select the branch with the minimum total route cost.
    # The Decision module (Step 2) independently scores & ranks hospitals by
    # clinical criteria (MCDA). Step 1 focuses purely on geographic proximity.
    logger.info("Pipeline Step 1: Task 1 (Multi-Target Route Optimization)...")

    multi_route_res = find_closest_suitable_hospital(
        source_id=source_loc_id,
        required_specialization=patient.required_specialization,
        algorithm='astar',
        heuristic='haversine',
        log_result=True,
    )

    # Extract the winning branch for downstream use
    closest_branch = multi_route_res.get('closest_hospital') or {}
    route_res = {
        'path':            closest_branch.get('path', []),
        'path_nodes':      closest_branch.get('path_nodes', []),
        'total_distance':  closest_branch.get('total_distance', 0.0),
        'total_time_min':  closest_branch.get('total_time_min', 0.0),
        'nodes_explored':  closest_branch.get('nodes_explored', 0),
        'execution_time_ms': closest_branch.get('execution_time_ms', 0.0),
        'memory_kb':       closest_branch.get('memory_kb', 0.0),
        'found':           multi_route_res.get('found', False),
        'algorithm':       'astar',
        'heuristic':       'haversine',
        'candidates_evaluated':  multi_route_res.get('candidates_evaluated', 0),
        'branches_excluded':     multi_route_res.get('branches_excluded', 0),
        'branches_unreachable':  multi_route_res.get('branches_unreachable', 0),
        'per_branch_comparison': multi_route_res.get('per_branch_comparison', []),
        'total_search_time_ms':  multi_route_res.get('total_search_time_ms', 0.0),
        'error':           multi_route_res.get('error'),
    }

    # ------------------------------------------------------------------------
    # STEP 2: Task 4 – Intelligent Decision (Compare Hospitals & Doctors)
    # ------------------------------------------------------------------------
    logger.info("Pipeline Step 2: Task 4 (Intelligent Decision)...")
    decision_res = recommend_hospital(patient, algorithm='weighted_ranking', log_result=True)
    recommended_hosp = decision_res.get('recommended_hospital') or {}
    rec_hospital_id = recommended_hosp.get('hospital_id', 1)

    # Prefer the route-optimized closest branch as the final destination;
    # fall back to MCDA recommendation if route search failed.
    if multi_route_res.get('found') and closest_branch.get('hospital_id'):
        rec_hospital_id = closest_branch['hospital_id']
        hosp_loc_id     = closest_branch['location_id']
    else:
        hosp_loc_id = recommended_hosp.get('location_id')
        if not hosp_loc_id:
            h_row = query_db("SELECT location_id FROM hospitals WHERE id = %s",
                             (rec_hospital_id,), one=True)
            hosp_loc_id = h_row['location_id'] if h_row else rec_hospital_id

    # ------------------------------------------------------------------------
    # STEP 3: Task 2 – Resource Allocation (Allocate Doctor, Room, Bed, Equipment)
    # ------------------------------------------------------------------------
    logger.info("Pipeline Step 3: Task 2 (Resource Allocation)...")
    allocation_res = run_resource_allocation(algorithm='greedy', log_result=True)

    # ------------------------------------------------------------------------
    # STEP 4: Task 3 – Network Analysis (Analyze Hospital Department Connections)
    # ------------------------------------------------------------------------
    logger.info("Pipeline Step 4: Task 3 (Network Analysis)...")
    network_res = run_network_analysis(algorithm='floyd_warshall', start_node_id=source_loc_id, log_result=True)

    # ------------------------------------------------------------------------
    # STEP 5: Task 5 – Optimization (Doctor & Room Schedule Optimization)
    # ------------------------------------------------------------------------
    logger.info("Pipeline Step 5: Task 5 (Schedule Optimization)...")
    scheduling_res = optimize_schedule(algorithm='ga', limit_appointments=4, log_result=True)

    # Optional Ambulance Transport Details
    if require_ambulance:
        booking_ref = f"AMB-{uuid.uuid4().hex[:8].upper()}"
        base_fare = 1500.0  # LKR base fare
        km_fare = round(route_res.get('total_distance', 10.0) * 150.0, 2)
        total_amount = base_fare + km_fare

        ambulance_booking = {
            'required': True,
            'booking_reference': booking_ref,
            'status': 'CONFIRMED',
            'assigned_hospital': recommended_hosp.get('hospital_name', 'National Hospital'),
            'pickup_location_id': source_loc_id,
            'destination_hospital_id': rec_hospital_id,
            'distance_km': route_res.get('total_distance', 0.0),
            'estimated_eta_min': route_res.get('total_time_min', 0.0),
            'payment': {
                'status': 'PAID',
                'currency': 'LKR',
                'base_fare': base_fare,
                'distance_fare': km_fare,
                'total_amount': total_amount,
                'transaction_id': f"TXN-{uuid.uuid4().hex[:10].upper()}",
                'payment_method': 'Online Emergency Clearance',
                'timestamp': datetime.now().isoformat(),
            }
        }
    else:
        ambulance_booking = {
            'required': False,
            'booking_reference': 'N/A (Self Transport)',
            'status': 'NOT_REQUESTED',
            'assigned_hospital': recommended_hosp.get('hospital_name', 'National Hospital'),
            'pickup_location_id': source_loc_id,
            'destination_hospital_id': rec_hospital_id,
            'distance_km': route_res.get('total_distance', 0.0),
            'estimated_eta_min': route_res.get('total_time_min', 0.0),
            'payment': None
        }

    # ------------------------------------------------------------------------
    # Master Assembly & Database Persistence
    # ------------------------------------------------------------------------
    pipeline_duration_ms = (datetime.now() - pipeline_start).total_seconds() * 1000

    master_result = {
        'session_id': session_id,
        'pipeline_status': 'COMPLETED',
        'pipeline_duration_ms': round(pipeline_duration_ms, 2),
        'patient': patient.to_dict(),
        'step_1_route': route_res,
        'step_2_decision': decision_res,
        'step_3_allocation': allocation_res,
        'step_4_network': network_res,
        'step_5_scheduling': scheduling_res,
        # Backwards compatibility keys
        'step_1_decision': decision_res,
        'step_2_allocation': allocation_res,
        'step_3_network': network_res,
        'step_4_route': route_res,
        'step_5_ambulance_booking': ambulance_booking,
        'step_6_scheduling': scheduling_res,
    }


    # Insert into emergency_requests table
    er_sql = """
        INSERT INTO emergency_requests (
            patient_id, emergency_level, required_specialization, preferred_date, preferred_time_slot,
            source_location_id, required_resources, status,
            result_json, recommended_hospital_id, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    er_id = execute_db(
        er_sql,
        (
            patient.patient_id,
            patient.emergency_level,
            patient.required_specialization or 'General',
            preferred_date or None,
            preferred_time_slot or 'morning',
            source_loc_id,
            json.dumps(patient.required_resources),
            'completed',
            json.dumps(master_result),
            rec_hospital_id,
            created_by_user_id,
        )
    )

    master_result['emergency_request_id'] = er_id
    logger.info("Pipeline completed successfully for Emergency Request ID #%d", er_id)

    # ------------------------------------------------------------------------
    # Also save the generated appointment into the appointments table
    # ------------------------------------------------------------------------
    try:
        appt_date = preferred_date or datetime.now().strftime('%Y-%m-%d')
        start_t = '09:00:00'
        end_t = '09:30:00'
        if preferred_time_slot == 'afternoon':
            start_t, end_t = '14:00:00', '14:30:00'
        elif preferred_time_slot == 'evening':
            start_t, end_t = '17:00:00', '17:30:00'

        room_no = f"Room {((patient.patient_id or 1) % 20) + 1:02d}"
        rec_doctor_id = recommended_hosp.get('assigned_doctor_id') or 1
        
        if not rec_doctor_id or rec_doctor_id == 1:
            doc_row = query_db("SELECT id FROM doctors WHERE hospital_id = %s LIMIT 1", (rec_hospital_id,), one=True)
            if doc_row:
                rec_doctor_id = doc_row['id']

        appt_sql = """
            INSERT INTO appointments (
                patient_id, doctor_id, hospital_id, room_number, appointment_date,
                start_time, end_time, duration_min, status, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        appt_id = execute_db(
            appt_sql,
            (
                patient.patient_id,
                rec_doctor_id,
                rec_hospital_id,
                room_no,
                appt_date,
                start_t,
                end_t,
                30,
                'scheduled',
                f"Emergency Care Plan #{session_id[:8]} - {patient.required_specialization or 'General'} consultation"
            )
        )
        master_result['appointment_id'] = appt_id
    except Exception as e:
        logger.error("Failed to insert appointment into appointments table: %s", e)

    return master_result

