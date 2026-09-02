"""
algorithms/network/floyd_warshall.py
======================================
Module 3 — Network Analysis: Floyd-Warshall All-Pairs Shortest Path Algorithm

PROBLEM STATEMENT
-----------------
Compute the shortest path distance between EVERY pair of nodes in the hospital
road network graph.

WHY FLOYD-WARSHALL?
-------------------
Floyd-Warshall is a DYNAMIC PROGRAMMING algorithm that solves the All-Pairs
Shortest Path (APSP) problem in O(V³) time and O(V²) space.

  Recurrence:
    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])

  where k considers intermediate nodes from 1 to V.

DATA STRUCTURE REQUIREMENT: Adjacency Matrix
---------------------------------------------
Floyd-Warshall requires O(1) random access to dist[i][j].
It converts the Graph's adjacency list into a V×V distance matrix using
`graph.to_adjacency_matrix()`.

COMPLEXITY
----------
  Time  : O(V³)   — triple nested loop over all node triples (i, j, k)
  Space : O(V²)   — V×V distance and predecessor matrices

USE IN MEDIROUTE
----------------
  - Precomputes shortest distances between ALL Sri Lankan hospital locations.
  - Used for hospital catchment area analysis and network bottleneck detection.
  - Compared with running Dijkstra V times:
      - V × Dijkstra: O(V × (V+E) log V) = O(V² log V) for sparse graphs
      - Floyd-Warshall: O(V³) regardless of density
"""

import time
import tracemalloc
from typing import Any, Dict, List, Tuple

from data_structures.graph import Graph


def floyd_warshall(graph: Graph) -> Dict[str, Any]:
    """
    Floyd-Warshall All-Pairs Shortest Path Algorithm.

    Primary algorithm for Module 3 (Network Analysis).

    Parameters
    ----------
    graph : Graph instance (adjacency list converted to matrix inside)

    Returns
    -------
    dict with keys:
        distance_matrix : list[list[float]] — V×V shortest distances
        path_matrix     : list[list[int]]   — next-hop node indices for path reconstruction
        node_map        : dict[int, int]    — node_id → matrix index
        index_to_id     : dict[int, int]    — matrix index → node_id
        node_count      : int
        execution_time_ms : float
        memory_kb       : float
        algorithm       : 'floyd_warshall'
    """
    if graph.node_count == 0:
        return _empty_result("Graph is empty")

    tracemalloc.start()
    t_start = time.perf_counter()

    INF = float('inf')

    # Convert adjacency list to V×V matrix
    dist_matrix, id_to_index, index_to_id = graph.to_adjacency_matrix()
    n = len(dist_matrix)

    # Path reconstruction matrix: next_hop[i][j] stores the next node on shortest path i → j
    next_hop: List[List[int]] = [[-1] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j and dist_matrix[i][j] < INF:
                next_hop[i][j] = j

    # Triple nested loop: dynamic programming
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist_matrix[i][k] < INF and dist_matrix[k][j] < INF:
                    new_dist = dist_matrix[i][k] + dist_matrix[k][j]
                    if new_dist < dist_matrix[i][j]:
                        dist_matrix[i][j] = new_dist
                        next_hop[i][j] = next_hop[i][k]

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        'distance_matrix': dist_matrix,
        'path_matrix': next_hop,
        'id_to_index': id_to_index,
        'index_to_id': index_to_id,
        'node_count': n,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'floyd_warshall',
        'error': None,
    }


def reconstruct_fw_path(
    floyd_result: Dict[str, Any],
    source_id: int,
    goal_id: int,
) -> Tuple[List[int], float]:
    """
    Reconstruct the shortest path between source_id and goal_id
    from the Floyd-Warshall result.

    Time: O(path length)
    """
    id_to_idx = floyd_result['id_to_index']
    idx_to_id = floyd_result['index_to_id']
    dist_matrix = floyd_result['distance_matrix']
    next_hop = floyd_result['path_matrix']

    if source_id not in id_to_idx or goal_id not in id_to_idx:
        return [], float('inf')

    u = id_to_idx[source_id]
    v = id_to_idx[goal_id]

    if dist_matrix[u][v] == float('inf'):
        return [], float('inf')

    path = [source_id]
    curr = u
    while curr != v:
        curr = next_hop[curr][v]
        if curr == -1:
            return [], float('inf')
        path.append(idx_to_id[curr])

    return path, dist_matrix[u][v]


def _empty_result(error: str) -> Dict[str, Any]:
    return {
        'distance_matrix': [], 'path_matrix': [],
        'id_to_index': {}, 'index_to_id': {},
        'node_count': 0,
        'execution_time_ms': 0.0, 'memory_kb': 0.0,
        'algorithm': 'floyd_warshall', 'error': error,
    }
