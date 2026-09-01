"""
services/route_service.py
==========================
Service for Module 1 (Route Optimization).

Fetches Sri Lankan locations & road routes from MySQL, builds the `Graph` data
structure, executes A*, Dijkstra, and BFS algorithms, logs metrics to DB,
and returns structured comparison results for the API and frontend.

Key Functions
-------------
find_optimal_route()              — Single-target A*/Dijkstra/BFS route.
find_closest_suitable_hospital()  — Multi-target strategy:
                                    1. Filter branches by required service/specialization.
                                    2. Run A* from patient location to EACH eligible branch.
                                    3. Return closest reachable branch + per-branch metrics.
compare_route_algorithms()        — A* vs Dijkstra vs BFS comparison on same input.
"""

import uuid
import logging
from typing import Any, Dict, List, Optional

from database.db import query_db
from data_structures.graph import Graph
from algorithms.route.astar import astar
from algorithms.route.dijkstra import dijkstra
from algorithms.route.bfs_route import bfs_shortest_path
from services.performance_service import log_algorithm_result

logger = logging.getLogger(__name__)


def load_hospital_network_graph() -> Graph:
    """
    Fetch locations and routes from MySQL and build Graph data structure.

    Returns
    -------
    Graph : Weighted Graph instance containing Sri Lankan road network.
    """
    locations = query_db(
        "SELECT id, name, latitude, longitude, location_type FROM locations"
    ) or []

    routes = query_db(
        "SELECT source_location_id, destination_location_id, distance_km, "
        "travel_time_min, traffic_level, is_bidirectional FROM routes"
    ) or []

    return Graph.from_db_data(locations, routes, directed=False)


def find_optimal_route(
    source_id: int,
    goal_id: int,
    algorithm: str = 'astar',
    heuristic: str = 'haversine',
    log_result: bool = True,
) -> Dict[str, Any]:
    """
    Run route optimization for a single requested algorithm.

    Parameters
    ----------
    source_id  : Source location node ID
    goal_id    : Destination location node ID
    algorithm  : 'astar' | 'dijkstra' | 'bfs'
    heuristic  : 'haversine' | 'euclidean' | 'zero' (for A*)
    log_result : Whether to log result to `algorithm_results` MySQL table

    Returns
    -------
    dict : Algorithmic route result with path, distance, metrics.
    """
    graph = load_hospital_network_graph()

    algo_lower = algorithm.lower()
    if algo_lower == 'astar':
        result = astar(graph, source_id, goal_id, heuristic=heuristic)
    elif algo_lower == 'dijkstra':
        result = dijkstra(graph, source_id, goal_id)
    elif algo_lower == 'bfs':
        result = bfs_shortest_path(graph, source_id, goal_id)
    else:
        raise ValueError(f"Unknown route algorithm: {algorithm}")

    if log_result and result.get('found'):
        log_algorithm_result(
            module='route',
            algorithm=algo_lower,
            execution_time_ms=result['execution_time_ms'],
            memory_kb=result['memory_kb'],
            solution_quality=100.0 if result['found'] else 0.0,
            input_size=graph.node_count,
            extra_metrics={
                'nodes_explored': result['nodes_explored'],
                'path_length': len(result['path']),
                'total_distance_km': result['total_distance'],
            },
            input_summary={'source_id': source_id, 'goal_id': goal_id},
            output_summary={'distance_km': result['total_distance'], 'nodes_explored': result['nodes_explored']},
        )

    return result


# ============================================================
# Multi-Target Strategy  (Chapter 3 §3.2 & §3.5)
# ============================================================

def find_closest_suitable_hospital(
    source_id: int,
    required_specialization: Optional[str] = None,
    algorithm: str = 'astar',
    heuristic: str = 'haversine',
    log_result: bool = True,
) -> Dict[str, Any]:
    """
    Task 1 — Multi-Target Route Strategy.

    Implements the branch-filtering + shortest-path pipeline described in
    Chapter 3 Section 3.2 / 3.5:

      Step 1 — Filter: Query active hospital branches from the DB and keep
                only those that offer the required specialization/service.
                Branches without a matching doctor specialization are excluded.

      Step 2 — Route: Load the road graph once, then run A* (or Dijkstra/BFS)
                from the patient's source_id to EACH eligible branch location.

      Step 3 — Select: Choose the branch with the minimum valid route cost
                (shortest total distance). Branches with no path are excluded.

      Step 4 — Return: The winning branch, its full route result, and a
                per-branch comparison table of all candidates evaluated.

    Parameters
    ----------
    source_id               : Patient's location node ID.
    required_specialization : Service filter (e.g. 'Cardiology'). If None,
                              all active branches are candidates.
    algorithm               : 'astar' | 'dijkstra' | 'bfs'
    heuristic               : A* heuristic ('haversine' | 'euclidean' | 'zero')
    log_result              : Log winning route to algorithm_results table.

    Returns
    -------
    dict with keys:
        found                  : bool
        closest_hospital       : dict  — winning hospital info + route
        candidates_evaluated   : int   — number of eligible branches checked
        branches_unreachable   : int   — branches with no valid path
        branches_excluded      : int   — branches filtered out by service
        per_branch_comparison  : list  — route result for every eligible branch
        algorithm              : str
        source_id              : int
        required_specialization: str | None
        error                  : str | None
    """
    import time
    t_start = time.perf_counter()

    # ── Step 1: Filter eligible hospital branches ───────────────────────────
    # Fetch all active hospitals
    all_hospitals = query_db(
        """
        SELECT h.id AS hospital_id, h.name AS hospital_name,
               h.location_id, l.name AS location_name,
               h.capacity, h.available_beds, h.icu_beds,
               h.available_icu_beds, h.rating, h.avg_wait_time_min
        FROM hospitals h
        JOIN locations l ON h.location_id = l.id
        WHERE h.status = 'active'
        """
    ) or []

    total_branches = len(all_hospitals)

    if required_specialization:
        # Keep only branches that have at least one doctor with matching specialization
        eligible = []
        for hosp in all_hospitals:
            doctors = query_db(
                """
                SELECT id FROM doctors
                WHERE hospital_id = %s
                  AND LOWER(specialization) LIKE %s
                  AND availability_status = 'available'
                LIMIT 1
                """,
                (hosp['hospital_id'], f"%{required_specialization.lower()}%"),
            ) or []
            if doctors:
                eligible.append(hosp)
    else:
        eligible = list(all_hospitals)

    branches_excluded = total_branches - len(eligible)

    if not eligible:
        return {
            'found': False,
            'closest_hospital': None,
            'candidates_evaluated': 0,
            'branches_unreachable': 0,
            'branches_excluded': branches_excluded,
            'per_branch_comparison': [],
            'algorithm': algorithm,
            'source_id': source_id,
            'required_specialization': required_specialization,
            'error': f"No active hospital branches provide '{required_specialization}'",
        }

    # ── Step 2: Load graph once, run route algorithm to each eligible branch ─
    graph = load_hospital_network_graph()

    if not graph.has_node(source_id):
        return {
            'found': False,
            'closest_hospital': None,
            'candidates_evaluated': len(eligible),
            'branches_unreachable': len(eligible),
            'branches_excluded': branches_excluded,
            'per_branch_comparison': [],
            'algorithm': algorithm,
            'source_id': source_id,
            'required_specialization': required_specialization,
            'error': f"Patient source location {source_id} not found in road network graph",
        }

    per_branch: List[Dict[str, Any]] = []
    algo_lower = algorithm.lower()

    for hosp in eligible:
        goal_id = int(hosp['location_id'])
        branch_entry: Dict[str, Any] = {
            'hospital_id': hosp['hospital_id'],
            'hospital_name': hosp['hospital_name'],
            'location_id': goal_id,
            'location_name': hosp['location_name'],
            'available_beds': hosp['available_beds'],
            'available_icu_beds': hosp['available_icu_beds'],
            'rating': hosp['rating'],
        }

        if not graph.has_node(goal_id):
            branch_entry.update({'found': False, 'total_distance': float('inf'),
                                  'total_time_min': float('inf'),
                                  'error': f'Hospital node {goal_id} not in road graph'})
            per_branch.append(branch_entry)
            continue

        # Run the selected algorithm
        if algo_lower == 'astar':
            route_res = astar(graph, source_id, goal_id, heuristic=heuristic)
        elif algo_lower == 'dijkstra':
            route_res = dijkstra(graph, source_id, goal_id)
        elif algo_lower == 'bfs':
            route_res = bfs_shortest_path(graph, source_id, goal_id)
        else:
            raise ValueError(f"Unknown route algorithm: {algorithm}")

        branch_entry.update(route_res)
        per_branch.append(branch_entry)

    # ── Step 3: Select closest reachable branch ──────────────────────────────
    reachable = [b for b in per_branch if b.get('found')]
    branches_unreachable = len(per_branch) - len(reachable)

    if not reachable:
        return {
            'found': False,
            'closest_hospital': None,
            'candidates_evaluated': len(eligible),
            'branches_unreachable': branches_unreachable,
            'branches_excluded': branches_excluded,
            'per_branch_comparison': per_branch,
            'algorithm': algorithm,
            'source_id': source_id,
            'required_specialization': required_specialization,
            'error': 'No eligible branch is reachable from the patient location',
        }

    # Closest = minimum total_distance among reachable branches
    best = min(reachable, key=lambda b: b['total_distance'])

    # ── Step 4: Log winning route & return ──────────────────────────────────
    if log_result:
        log_algorithm_result(
            module='route',
            algorithm=algo_lower,
            execution_time_ms=best.get('execution_time_ms', 0),
            memory_kb=best.get('memory_kb', 0),
            solution_quality=100.0,
            input_size=graph.node_count,
            extra_metrics={
                'candidates_evaluated': len(eligible),
                'branches_excluded': branches_excluded,
                'branches_unreachable': branches_unreachable,
                'nodes_explored': best.get('nodes_explored', 0),
                'total_distance_km': best.get('total_distance', 0),
            },
            input_summary={
                'source_id': source_id,
                'required_specialization': required_specialization,
                'algorithm': algorithm,
            },
            output_summary={
                'closest_hospital': best['hospital_name'],
                'distance_km': best['total_distance'],
            },
        )

    total_time_ms = (time.perf_counter() - t_start) * 1000

    return {
        'found': True,
        'closest_hospital': best,
        'candidates_evaluated': len(eligible),
        'branches_unreachable': branches_unreachable,
        'branches_excluded': branches_excluded,
        'per_branch_comparison': per_branch,
        'total_search_time_ms': round(total_time_ms, 2),
        'algorithm': algorithm,
        'source_id': source_id,
        'required_specialization': required_specialization,
        'error': None,
    }


def compare_route_algorithms(source_id: int, goal_id: int) -> Dict[str, Any]:
    """
    Run A*, Dijkstra, and BFS on the SAME input to generate comparative evaluation.

    Used by Algorithm Lab and Performance Dashboard.
    """
    graph = load_hospital_network_graph()
    session_id = str(uuid.uuid4())

    a_res = astar(graph, source_id, goal_id, heuristic='haversine')
    d_res = dijkstra(graph, source_id, goal_id)
    b_res = bfs_shortest_path(graph, source_id, goal_id)

    # Log all three with the same session_id for benchmark grouping
    for res in (a_res, d_res, b_res):
        if res.get('found'):
            log_algorithm_result(
                module='route',
                algorithm=res['algorithm'],
                execution_time_ms=res['execution_time_ms'],
                memory_kb=res['memory_kb'],
                solution_quality=100.0 if res['found'] else 0.0,
                input_size=graph.node_count,
                extra_metrics={'nodes_explored': res['nodes_explored'], 'distance_km': res['total_distance']},
                session_id=session_id,
            )

    return {
        'source_id': source_id,
        'goal_id': goal_id,
        'session_id': session_id,
        'algorithms': {
            'astar': a_res,
            'dijkstra': d_res,
            'bfs': b_res,
        },
        'summary_comparison': [
            {
                'algorithm': 'A* (Haversine)',
                'nodes_explored': a_res['nodes_explored'],
                'execution_time_ms': round(a_res['execution_time_ms'], 4),
                'distance_km': a_res['total_distance'],
                'path_length': len(a_res['path']),
                'efficiency_gain': f"{((d_res['nodes_explored'] - a_res['nodes_explored']) / max(1, d_res['nodes_explored'])) * 100:.1f}% fewer nodes than Dijkstra",
            },
            {
                'algorithm': "Dijkstra's",
                'nodes_explored': d_res['nodes_explored'],
                'execution_time_ms': round(d_res['execution_time_ms'], 4),
                'distance_km': d_res['total_distance'],
                'path_length': len(d_res['path']),
                'efficiency_gain': 'Baseline (100% nodes explored)',
            },
            {
                'algorithm': 'BFS (Unweighted)',
                'nodes_explored': b_res['nodes_explored'],
                'execution_time_ms': round(b_res['execution_time_ms'], 4),
                'distance_km': b_res['total_distance'],
                'path_length': len(b_res['path']),
                'efficiency_gain': 'Optimizes hops, not distance (Suboptimal distance)',
            },
        ],
    }
