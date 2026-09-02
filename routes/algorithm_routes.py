"""
routes/algorithm_routes.py
===========================
REST API routes for triggering pure Python algorithm execution on demand.

API Endpoints:
  POST /api/route/run       — Run A*, Dijkstra, or BFS
  POST /api/allocation/run  — Run Greedy or Hungarian allocation
  POST /api/network/run     — Run BFS, DFS, or Floyd-Warshall
  POST /api/decision/run    — Run Weighted Ranking or Decision Tree
  POST /api/scheduling/run  — Run Greedy, GA, or Brute Force
"""

import logging
from flask import Blueprint, request, jsonify

from routes.auth_routes import login_required
from data_structures.patient import Patient
from services.route_service import find_optimal_route, compare_route_algorithms
from services.allocation_service import run_resource_allocation, compare_allocation_algorithms
from services.network_service import run_network_analysis, compare_network_algorithms
from services.decision_service import recommend_hospital, compare_decision_algorithms
from services.scheduling_service import optimize_schedule, compare_scheduling_algorithms

logger = logging.getLogger(__name__)

algo_api_bp = Blueprint('algo_api', __name__, url_prefix='/api')


# ── Module 1: Route Optimization ──
@algo_api_bp.route('/route/run', methods=['POST'])
@login_required
def api_run_route():
    data = request.get_json() or {}
    source_id = int(data.get('source_id', 1))
    goal_id = int(data.get('goal_id', 8))
    algo = data.get('algorithm', 'astar')

    if data.get('compare'):
        res = compare_route_algorithms(source_id, goal_id)
    else:
        res = find_optimal_route(source_id, goal_id, algorithm=algo)
    return jsonify(res)


# ── Module 2: Resource Allocation ──
@algo_api_bp.route('/allocation/run', methods=['POST'])
@login_required
def api_run_allocation():
    data = request.get_json() or {}
    algo = data.get('algorithm', 'greedy')

    if data.get('compare'):
        res = compare_allocation_algorithms()
    else:
        res = run_resource_allocation(algorithm=algo)
    return jsonify(res)


# ── Module 3: Network Analysis ──
@algo_api_bp.route('/network/run', methods=['POST'])
@login_required
def api_run_network():
    data = request.get_json() or {}
    algo = data.get('algorithm', 'floyd_warshall')
    start_node = int(data.get('start_node_id', 1))

    if data.get('compare'):
        res = compare_network_algorithms(start_node)
    else:
        res = run_network_analysis(algorithm=algo, start_node_id=start_node)
    return jsonify(res)


# ── Module 4: Intelligent Decision Support ──
@algo_api_bp.route('/decision/run', methods=['POST'])
@login_required
def api_run_decision():
    data = request.get_json() or {}
    algo = data.get('algorithm', 'weighted_ranking')
    p_id = int(data.get('patient_id', 1))
    spec = data.get('specialization', 'Cardiology')

    p = Patient(patient_id=p_id, name='Demo Patient', emergency_level='critical', location_id=1, required_specialization=spec)

    if data.get('compare'):
        res = compare_decision_algorithms(p)
    else:
        res = recommend_hospital(p, algorithm=algo)
    return jsonify(res)


# ── Module 5: Scheduling Optimization ──
@algo_api_bp.route('/scheduling/run', methods=['POST'])
@login_required
def api_run_scheduling():
    data = request.get_json() or {}
    algo = data.get('algorithm', 'ga')
    limit = int(data.get('limit', 6))

    if data.get('compare'):
        res = compare_scheduling_algorithms(limit_appointments=limit)
    else:
        res = optimize_schedule(algorithm=algo, limit_appointments=limit)
    return jsonify(res)
