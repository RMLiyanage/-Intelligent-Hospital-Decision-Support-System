"""
algorithms/network/bfs_dfs.py
==============================
Module 3 — Network Analysis: BFS & DFS Graph Traversal

PROBLEM STATEMENT
-----------------
Analyze the hospital facility network topology:
  1. BFS: Level-order exploration to find connected components and shortest hop paths.
  2. DFS: Depth-first traversal for bottleneck identification and cycle detection.

COMPLEXITY
----------
  BFS Time: O(V + E)  Space: O(V)  [Queue-based]
  DFS Time: O(V + E)  Space: O(V)  [Stack/Recursion-based]

USES IN MEDIROUTE
-----------------
  - Check whether every hospital location is connected to the emergency road network.
  - Count connected components in Sri Lanka's road graph.
  - Calculate graph diameter and average degree.
"""

import time
import tracemalloc
from collections import deque
from typing import Any, Dict, List, Set, Tuple

from data_structures.graph import Graph


def bfs_traversal(graph: Graph, start_node_id: int) -> Dict[str, Any]:
    """
    Breadth-First Search graph traversal.

    Parameters
    ----------
    graph         : Graph instance
    start_node_id : Node ID to start traversal from

    Returns
    -------
    dict with keys:
        traversal_order : list[int] — node IDs in visit order
        visit_names     : list[str] — node names in visit order
        levels          : dict[int, int] — node_id → distance in hops from start
        visited_count   : int
        total_nodes     : int
        execution_time_ms : float
        memory_kb       : float
        algorithm       : 'bfs_traversal'
    """
    if not graph.has_node(start_node_id):
        return _empty_traversal('bfs_traversal', f"Start node {start_node_id} not in graph")

    tracemalloc.start()
    t_start = time.perf_counter()

    visited: Set[int] = {start_node_id}
    queue: deque = deque([(start_node_id, 0)])
    traversal_order: List[int] = []
    levels: Dict[int, int] = {}

    while queue:
        node_id, level = queue.popleft()
        traversal_order.append(node_id)
        levels[node_id] = level

        for neighbor_id in graph.get_neighbor_ids(node_id):
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append((neighbor_id, level + 1))

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        'traversal_order': traversal_order,
        'visit_names': [graph.get_node(n).name for n in traversal_order],
        'levels': levels,
        'visited_count': len(traversal_order),
        'total_nodes': graph.node_count,
        'is_connected': len(traversal_order) == graph.node_count,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'bfs_traversal',
        'error': None,
    }


def dfs_traversal(graph: Graph, start_node_id: int) -> Dict[str, Any]:
    """
    Depth-First Search graph traversal (iterative with explicit stack).

    Parameters
    ----------
    graph         : Graph instance
    start_node_id : Node ID to start traversal from

    Returns
    -------
    dict with keys: Same schema as bfs_traversal().
    """
    if not graph.has_node(start_node_id):
        return _empty_traversal('dfs_traversal', f"Start node {start_node_id} not in graph")

    tracemalloc.start()
    t_start = time.perf_counter()

    visited: Set[int] = set()
    stack: List[int] = [start_node_id]
    traversal_order: List[int] = []

    while stack:
        node_id = stack.pop()
        if node_id not in visited:
            visited.add(node_id)
            traversal_order.append(node_id)

            # Push neighbors in reverse to visit in natural order
            neighbors = graph.get_neighbor_ids(node_id)
            for neighbor_id in reversed(neighbors):
                if neighbor_id not in visited:
                    stack.append(neighbor_id)

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        'traversal_order': traversal_order,
        'visit_names': [graph.get_node(n).name for n in traversal_order],
        'levels': {},
        'visited_count': len(traversal_order),
        'total_nodes': graph.node_count,
        'is_connected': len(traversal_order) == graph.node_count,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'dfs_traversal',
        'error': None,
    }


def find_connected_components(graph: Graph) -> Dict[str, Any]:
    """
    Find all connected components in the hospital road graph using BFS.

    Returns
    -------
    dict : component count, component list of node IDs/names
    """
    tracemalloc.start()
    t_start = time.perf_counter()

    visited: Set[int] = set()
    components: List[List[int]] = []

    for node in graph.get_all_nodes():
        node_id = node.node_id
        if node_id not in visited:
            # Run BFS for this component
            comp = []
            queue = deque([node_id])
            visited.add(node_id)

            while queue:
                curr = queue.popleft()
                comp.append(curr)
                for nxt in graph.get_neighbor_ids(curr):
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)

            components.append(comp)

    t_end = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        'component_count': len(components),
        'components': [
            {
                'size': len(c),
                'node_ids': c,
                'node_names': [graph.get_node(nid).name for nid in c],
            }
            for c in components
        ],
        'total_nodes': graph.node_count,
        'execution_time_ms': (t_end - t_start) * 1000,
        'memory_kb': peak_mem / 1024,
        'algorithm': 'connected_components',
        'error': None,
    }


def _empty_traversal(algo: str, error: str) -> Dict[str, Any]:
    return {
        'traversal_order': [], 'visit_names': [], 'levels': {},
        'visited_count': 0, 'total_nodes': 0, 'is_connected': False,
        'execution_time_ms': 0.0, 'memory_kb': 0.0,
        'algorithm': algo, 'error': error,
    }
