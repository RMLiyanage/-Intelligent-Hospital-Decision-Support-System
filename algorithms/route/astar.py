"""
algorithms/route/astar.py
==========================
Module 1 — Route Optimization: A* Search Algorithm

PROBLEM STATEMENT
-----------------
Given the Sri Lankan hospital road network (weighted graph), find the
OPTIMAL (shortest distance) path from a patient's current location to
a destination hospital.

WHY A*?
-------
A* is OPTIMAL and COMPLETE when the heuristic is ADMISSIBLE
(never overestimates the true cost).

A* combines:
  g(n) = actual distance from source to node n
  h(n) = estimated distance from n to goal (Euclidean / Haversine)
  f(n) = g(n) + h(n)   ← the priority queue ordering key

  Compared to Dijkstra:
    - Dijkstra:   f(n) = g(n)        — explores uniformly in all directions
    - A*:         f(n) = g(n) + h(n) — directs search toward the goal
    - BFS:        unweighted, finds fewest hops, ignores distance

  Result: A* explores FEWER nodes than Dijkstra for geographic graphs.

DATA STRUCTURES USED
--------------------
  Open Set   : PriorityQueue (min-heap) — ordered by f-score
               Contains nodes to be evaluated
  Closed Set : set() — O(1) membership check for visited nodes
  came_from  : dict — reconstructs the path from goal to source
  g_score    : dict — best known distance from source to each node

COMPLEXITY
----------
  Time  : O((V + E) log V)  — heap operations per edge relaxation
  Space : O(V)              — g_score, came_from, open/closed sets

HEURISTIC
---------
Haversine formula computes great-circle distance between two GPS
coordinates. This is ADMISSIBLE because it computes straight-line
distance (always ≤ actual road distance).

EXPERIMENTAL EVALUATION
------------------------
The function records execution metrics to the `algorithm_results` table:
  - execution_time_ms
  - nodes_explored
  - path_length
  - solution quality
"""

import math
import time
import tracemalloc
from typing import Dict, List, Optional, Tuple, Any

from data_structures.graph import Graph, GraphNode
from data_structures.priority_queue import PriorityQueue


# ============================================================
# Heuristic Function
# ============================================================

def haversine_distance(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
    """
    Haversine formula — great-circle distance in km.

    ADMISSIBLE HEURISTIC for A*:
      Road distance ≥ straight-line distance ← proved by triangle inequality

    This guarantees A* finds the optimal (shortest) path.

    Parameters
    ----------
    lat1, lon1 : Source GPS coordinates (degrees)
    lat2, lon2 : Destination GPS coordinates (degrees)

    Returns
    -------
    float : Distance in km (straight-line, never > road distance)

    Time: O(1)
    """
    R = 6371.0  # Earth's radius in km
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def euclidean_heuristic(node: GraphNode, goal: GraphNode) -> float:
    """
    Euclidean distance heuristic using GPS coordinates.

    Less accurate than Haversine for large distances (Earth curvature)
    but still admissible and faster to compute.

    Used for algorithm lab comparison with Haversine.
    """
    dlat = node.latitude - goal.latitude
    dlon = node.longitude - goal.longitude
    # Approximate: 1° ≈ 111 km
    return math.sqrt((dlat * 111) ** 2 + (dlon * 111) ** 2)


def zero_heuristic(_node: GraphNode, _goal: GraphNode) -> float:
    """
    Zero heuristic — degenerates A* into Dijkstra's algorithm.

    Used for algorithm comparison: running A* with h=0 gives
    identical results to Dijkstra but allows same code path.
    """
    return 0.0


# ============================================================
# A* Algorithm
# ============================================================

def astar(
    graph: Graph,
    source_id: int,
    goal_id: int,
    heuristic: str = 'haversine',
) -> Dict[str, Any]:
    """
    A* Search Algorithm for shortest path in the hospital road network.

    This is the PRIMARY algorithm for Module 1 (Route Optimization).

    Algorithm Steps:
    ----------------
    1. Initialise:
         open_set = PriorityQueue()
         closed_set = set()
         g_score[source] = 0
         f_score[source] = h(source, goal)
         open_set.push(source, f_score[source])
         came_from = {}

    2. While open_set is not empty:
         current = open_set.pop()  ← lowest f-score

         If current == goal: RETURN reconstructed path

         Add current to closed_set

         For each neighbor of current:
             If neighbor in closed_set: skip
             tentative_g = g_score[current] + edge.weight

             If tentative_g < g_score[neighbor]:
                 came_from[neighbor] = current
                 g_score[neighbor] = tentative_g
                 f_score[neighbor] = tentative_g + h(neighbor, goal)
                 open_set.push(neighbor, f_score[neighbor])

    3. Return empty path (goal unreachable)

    Parameters
    ----------
    graph      : Weighted undirected graph of hospital road network
    source_id  : Start node (patient's location)
    goal_id    : Destination node (hospital location)
    heuristic  : 'haversine' (default) | 'euclidean' | 'zero'

    Returns
    -------
    dict with keys:
        path           : list[int]  — node IDs from source to goal
        path_nodes     : list[str]  — node names from source to goal
        total_distance : float      — total path distance in km
        total_time_min : float      — estimated travel time in minutes
        nodes_explored : int        — nodes popped from open set
        execution_time_ms : float   — wall-clock time
        memory_kb      : float      — peak memory during run
        found          : bool       — True if path was found
        algorithm      : str        — always 'astar'
        heuristic      : str        — heuristic used

    Time  : O((V + E) log V)
    Space : O(V)
    """

    # ── Choose heuristic function ──
    heur_fn = {
        'haversine': lambda n, g: haversine_distance(n.latitude, n.longitude,
                                                      g.latitude, g.longitude),
        'euclidean': euclidean_heuristic,
        'zero':      zero_heuristic,
    }.get(heuristic, lambda n, g: haversine_distance(n.latitude, n.longitude,
                                                      g.latitude, g.longitude))

    # ── Input validation ──
    if not graph.has_node(source_id):
        return _empty_result('astar', heuristic, f"Source node {source_id} not in graph")
    if not graph.has_node(goal_id):
        return _empty_result('astar', heuristic, f"Goal node {goal_id} not in graph")
    if source_id == goal_id:
        node = graph.get_node(source_id)
        return {
            'path': [source_id],
            'path_nodes': [node.name],
            'total_distance': 0.0,
            'total_time_min': 0.0,
            'nodes_explored': 0,
            'execution_time_ms': 0.0,
            'memory_kb': 0.0,
            'found': True,
            'algorithm': 'astar',
            'heuristic': heuristic,
            'error': None,
        }

    # ── Start timing and memory tracking ──
    tracemalloc.start()
    t_start = time.perf_counter()

    goal_node = graph.get_node(goal_id)
    INF = float('inf')

    # ── Data structures ──
    open_set: PriorityQueue = PriorityQueue()
    closed_set: set = set()
    came_from: Dict[int, int] = {}
    g_score: Dict[int, float] = {node.node_id: INF for node in graph.get_all_nodes()}
    g_score[source_id] = 0.0

    source_node = graph.get_node(source_id)
    f_initial = heur_fn(source_node, goal_node)
    open_set.push(source_id, f_initial)

    nodes_explored: int = 0

    # ── Main loop ──
    while not open_set.is_empty():
        current_id = open_set.pop()
        nodes_explored += 1

        # GOAL REACHED ─ reconstruct path
        if current_id == goal_id:
            t_end = time.perf_counter()
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            path = _reconstruct_path(came_from, current_id)
            distance, travel_time = _path_metrics(graph, path)

            return {
                'path': path,
                'path_nodes': [graph.get_node(n).name for n in path],
                'total_distance': round(distance, 2),
                'total_time_min': round(travel_time, 1),
                'nodes_explored': nodes_explored,
                'execution_time_ms': (t_end - t_start) * 1000,
                'memory_kb': peak_mem / 1024,
                'found': True,
                'algorithm': 'astar',
                'heuristic': heuristic,
                'error': None,
            }

        closed_set.add(current_id)

        # ── Relax edges ──
        for edge in graph.get_neighbors(current_id):
            neighbor_id = edge.to_id

            if neighbor_id in closed_set:
                continue

            tentative_g = g_score[current_id] + edge.weight

            if tentative_g < g_score.get(neighbor_id, INF):
                came_from[neighbor_id] = current_id
                g_score[neighbor_id] = tentative_g

                neighbor_node = graph.get_node(neighbor_id)
                f = tentative_g + heur_fn(neighbor_node, goal_node)

                if open_set.contains(neighbor_id):
                    open_set.update_priority(neighbor_id, f)
                else:
                    open_set.push(neighbor_id, f)

    # ── Goal unreachable ──
    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        'path': [],
        'path_nodes': [],
        'total_distance': INF,
        'total_time_min': INF,
        'nodes_explored': nodes_explored,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'found': False,
        'algorithm': 'astar',
        'heuristic': heuristic,
        'error': f"No path from {source_id} to {goal_id}",
    }


# ============================================================
# Helper Functions
# ============================================================

def _reconstruct_path(came_from: Dict[int, int], current: int) -> List[int]:
    """
    Walk backwards through came_from to reconstruct path.

    Time: O(path length)
    """
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _path_metrics(graph: Graph, path: List[int]) -> Tuple[float, float]:
    """
    Compute total distance and travel time for a given path.

    Time: O(path length)
    """
    total_dist = 0.0
    total_time = 0.0
    for i in range(len(path) - 1):
        edge = graph.get_edge(path[i], path[i + 1])
        if edge:
            total_dist += edge.distance
            total_time += edge.effective_travel_time
    return total_dist, total_time


def _empty_result(algorithm: str, heuristic: str, error: str) -> Dict[str, Any]:
    return {
        'path': [],
        'path_nodes': [],
        'total_distance': 0.0,
        'total_time_min': 0.0,
        'nodes_explored': 0,
        'execution_time_ms': 0.0,
        'memory_kb': 0.0,
        'found': False,
        'algorithm': algorithm,
        'heuristic': heuristic,
        'error': error,
    }
