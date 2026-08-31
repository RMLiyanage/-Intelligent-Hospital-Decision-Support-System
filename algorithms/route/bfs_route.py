"""
algorithms/route/bfs_route.py
==============================
Module 1 — Route Optimization: BFS as comparison algorithm.

BFS finds the FEWEST-HOPS path (unweighted shortest path).
For road networks, this is SUBOPTIMAL — fewer stops does not mean
shorter distance.

BFS serves as EDUCATIONAL COMPARISON to show students WHY weighted
shortest path algorithms (A*, Dijkstra) are needed for real routing.

COMPARISON TABLE (Module 1 Algorithms):
┌──────────────┬─────────────────┬──────────────────────────────┐
│ Algorithm    │ Complexity      │ What it optimizes            │
├──────────────┼─────────────────┼──────────────────────────────┤
│ A*           │ O((V+E) log V)  │ Total distance (km) — BEST   │
│ Dijkstra     │ O((V+E) log V)  │ Total distance (km)          │
│ BFS          │ O(V + E)        │ Number of hops — SUBOPTIMAL  │
└──────────────┴─────────────────┴──────────────────────────────┘

DATA STRUCTURE: Queue (collections.deque) for O(1) append/popleft.
VISITED SET:    set() for O(1) membership check.
"""

import time
import tracemalloc
from collections import deque
from typing import Any, Dict, List, Optional

from data_structures.graph import Graph


def bfs_shortest_path(
    graph: Graph,
    source_id: int,
    goal_id: int,
) -> Dict[str, Any]:
    """
    BFS for unweighted shortest path (fewest hops).

    COMPARISON algorithm for Module 1.
    Not recommended for actual route optimization — use A* instead.

    Parameters
    ----------
    graph     : Road network graph (weights are IGNORED by BFS)
    source_id : Start node
    goal_id   : Destination node

    Returns
    -------
    dict : Same schema as astar() result for direct comparison.
           Note: total_distance is computed AFTER path is found
           by summing actual edge weights — BFS did not minimize this.
    """
    if not graph.has_node(source_id):
        return _empty(f"Source {source_id} not in graph")
    if not graph.has_node(goal_id):
        return _empty(f"Goal {goal_id} not in graph")

    tracemalloc.start()
    t_start = time.perf_counter()

    # BFS data structures
    queue: deque = deque([source_id])
    visited: set = {source_id}
    parent: Dict[int, Optional[int]] = {source_id: None}
    nodes_explored = 0

    found = False
    while queue:
        current = queue.popleft()
        nodes_explored += 1

        if current == goal_id:
            found = True
            break

        for neighbor_id in graph.get_neighbor_ids(current):
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                parent[neighbor_id] = current
                queue.append(neighbor_id)

    t_end = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if not found:
        return {
            'path': [], 'path_nodes': [],
            'total_distance': float('inf'), 'total_time_min': float('inf'),
            'nodes_explored': nodes_explored,
            'execution_time_ms': (t_end - t_start) * 1000,
            'memory_kb': peak / 1024,
            'found': False, 'algorithm': 'bfs',
            'error': f"No path from {source_id} to {goal_id}",
        }

    # Reconstruct path
    path = []
    node = goal_id
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()

    # Compute actual weighted distance AFTER path is found
    total_dist = 0.0
    total_time = 0.0
    for i in range(len(path) - 1):
        edge = graph.get_edge(path[i], path[i + 1])
        if edge:
            total_dist += edge.distance
            total_time += edge.effective_travel_time

    return {
        'path': path,
        'path_nodes': [graph.get_node(n).name for n in path],
        'total_distance': round(total_dist, 2),
        'total_time_min': round(total_time, 1),
        'nodes_explored': nodes_explored,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak / 1024,
        'found': True,
        'algorithm': 'bfs',
        'error': None,
    }


def _empty(error: str) -> Dict[str, Any]:
    return {
        'path': [], 'path_nodes': [],
        'total_distance': 0.0, 'total_time_min': 0.0,
        'nodes_explored': 0, 'execution_time_ms': 0.0,
        'memory_kb': 0.0, 'found': False,
        'algorithm': 'bfs', 'error': error,
    }
