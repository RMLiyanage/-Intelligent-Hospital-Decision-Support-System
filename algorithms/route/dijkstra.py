"""
algorithms/route/dijkstra.py
=============================
Module 1 — Route Optimization: Dijkstra's Algorithm

Used for COMPARISON with A* to demonstrate the performance difference.

KEY DIFFERENCE FROM A*
-----------------------
Dijkstra uses f(n) = g(n) only.
It expands nodes in order of increasing distance from source,
without using any heuristic to guide toward the goal.

For geographic graphs this means Dijkstra explores in a circular
wavefront — it considers nodes behind the source that are clearly
irrelevant to reaching a goal ahead.

A* cuts this exploration by adding h(n) (estimated distance to goal).

ALGORITHM STEPS
---------------
1. dist[source] = 0; dist[all others] = INF
2. open_set = PriorityQueue() with source at priority 0
3. While open_set:
     u = pop minimum
     For each neighbor v of u:
         new_dist = dist[u] + w(u,v)
         If new_dist < dist[v]:
             dist[v] = new_dist
             prev[v] = u
             open_set.push(v, new_dist)
4. Reconstruct path via prev[]

COMPLEXITY
----------
  Time  : O((V + E) log V)  — same asymptotic as A*
  Space : O(V)
  But explores more nodes in practice for geographic single-target queries.

EXPERIMENTAL USE
----------------
The comparison between A* and Dijkstra's node exploration counts
is the core evidence for the "Algorithm Comparison" section of the
PDSA report (Module 1 evaluation).
"""

import time
import tracemalloc
from typing import Any, Dict, List, Tuple

from data_structures.graph import Graph
from data_structures.priority_queue import PriorityQueue


def dijkstra(
    graph: Graph,
    source_id: int,
    goal_id: int,
) -> Dict[str, Any]:
    """
    Dijkstra's Shortest Path Algorithm.

    Comparison algorithm for Module 1 (vs A*).
    Same return format as astar() to enable direct comparison.

    Parameters
    ----------
    graph     : Weighted undirected graph
    source_id : Start node
    goal_id   : Destination node

    Returns
    -------
    dict : Same schema as astar() result for comparison.
    """
    if not graph.has_node(source_id):
        return _empty(f"Source {source_id} not in graph")
    if not graph.has_node(goal_id):
        return _empty(f"Goal {goal_id} not in graph")
    if source_id == goal_id:
        return {
            'path': [source_id],
            'path_nodes': [graph.get_node(source_id).name],
            'total_distance': 0.0, 'total_time_min': 0.0,
            'nodes_explored': 0, 'execution_time_ms': 0.0,
            'memory_kb': 0.0, 'found': True,
            'algorithm': 'dijkstra', 'error': None,
        }

    tracemalloc.start()
    t_start = time.perf_counter()

    INF = float('inf')
    dist: Dict[int, float]  = {n.node_id: INF for n in graph.get_all_nodes()}
    prev: Dict[int, int]    = {}
    dist[source_id] = 0.0

    open_set = PriorityQueue()
    open_set.push(source_id, 0.0)
    nodes_explored = 0

    while not open_set.is_empty():
        u = open_set.pop()
        nodes_explored += 1

        if u == goal_id:
            break  # Optimal path found — early exit for single-target

        for edge in graph.get_neighbors(u):
            v = edge.to_id
            nd = dist[u] + edge.weight
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                if open_set.contains(v):
                    open_set.update_priority(v, nd)
                else:
                    open_set.push(v, nd)

    t_end = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if dist[goal_id] == INF:
        return {
            'path': [], 'path_nodes': [],
            'total_distance': INF, 'total_time_min': INF,
            'nodes_explored': nodes_explored,
            'execution_time_ms': (t_end - t_start) * 1000,
            'memory_kb': peak / 1024,
            'found': False, 'algorithm': 'dijkstra',
            'error': f"No path from {source_id} to {goal_id}",
        }

    path = _reconstruct(prev, goal_id)
    total_dist, total_time = _path_metrics(graph, path)

    return {
        'path': path,
        'path_nodes': [graph.get_node(n).name for n in path],
        'total_distance': round(total_dist, 2),
        'total_time_min': round(total_time, 1),
        'nodes_explored': nodes_explored,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak / 1024,
        'found': True,
        'algorithm': 'dijkstra',
        'error': None,
    }


def dijkstra_all_pairs(graph: Graph) -> Dict[int, Dict[int, float]]:
    """
    Run Dijkstra from every node to compute all-pairs shortest paths.

    Used by the Network Analysis module as a reference implementation
    to validate Floyd-Warshall results.

    Time:  O(V × (V + E) log V)
    Space: O(V²)
    """
    all_dist = {}
    for node in graph.get_all_nodes():
        result = dijkstra(graph, node.node_id, -1)
        # Run full Dijkstra (no early exit — goal_id = -1 won't match)
        # We need a modified version without early exit here:
        all_dist[node.node_id] = _dijkstra_full(graph, node.node_id)
    return all_dist


def _dijkstra_full(graph: Graph, source_id: int) -> Dict[int, float]:
    """Dijkstra to all reachable nodes from source. No early exit."""
    INF = float('inf')
    dist = {n.node_id: INF for n in graph.get_all_nodes()}
    dist[source_id] = 0.0
    pq = PriorityQueue()
    pq.push(source_id, 0.0)
    while not pq.is_empty():
        u = pq.pop()
        for edge in graph.get_neighbors(u):
            v = edge.to_id
            nd = dist[u] + edge.weight
            if nd < dist[v]:
                dist[v] = nd
                if pq.contains(v):
                    pq.update_priority(v, nd)
                else:
                    pq.push(v, nd)
    return dist


def _reconstruct(prev: Dict[int, int], goal: int) -> List[int]:
    path = [goal]
    while goal in prev:
        goal = prev[goal]
        path.append(goal)
    path.reverse()
    return path


def _path_metrics(graph: Graph, path: List[int]) -> Tuple[float, float]:
    d = t = 0.0
    for i in range(len(path) - 1):
        edge = graph.get_edge(path[i], path[i + 1])
        if edge:
            d += edge.distance
            t += edge.effective_travel_time
    return d, t


def _empty(error: str) -> Dict[str, Any]:
    return {
        'path': [], 'path_nodes': [],
        'total_distance': 0.0, 'total_time_min': 0.0,
        'nodes_explored': 0, 'execution_time_ms': 0.0,
        'memory_kb': 0.0, 'found': False,
        'algorithm': 'dijkstra', 'error': error,
    }
