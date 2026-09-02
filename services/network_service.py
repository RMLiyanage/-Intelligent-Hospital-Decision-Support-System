"""
services/network_service.py
============================
Service for Module 3 (Network Analysis).

Analyzes hospital location network topology using BFS, DFS, and Floyd-Warshall.
"""

import uuid
import logging
from typing import Any, Dict, List, Optional

from database.db import query_db
from data_structures.graph import Graph
from algorithms.network.bfs_dfs import bfs_traversal, dfs_traversal, find_connected_components
from algorithms.network.floyd_warshall import floyd_warshall, reconstruct_fw_path
from services.performance_service import log_algorithm_result

logger = logging.getLogger(__name__)


def load_network_graph() -> Graph:
    """Fetch location nodes & routes from MySQL into Graph object."""
    locations = query_db("SELECT id, name, latitude, longitude, location_type FROM locations") or []
    routes = query_db("SELECT source_location_id, destination_location_id, distance_km, travel_time_min, traffic_level, is_bidirectional FROM routes") or []
    return Graph.from_db_data(locations, routes, directed=False)


def run_network_analysis(
    algorithm: str = 'floyd_warshall',
    start_node_id: int = 1,
    log_result: bool = True,
) -> Dict[str, Any]:
    """Run specified network analysis algorithm."""
    graph = load_network_graph()

    algo_lower = algorithm.lower()
    if algo_lower in ('bfs', 'bfs_traversal'):
        res = bfs_traversal(graph, start_node_id)
    elif algo_lower in ('dfs', 'dfs_traversal'):
        res = dfs_traversal(graph, start_node_id)
    elif algo_lower in ('components', 'connected_components'):
        res = find_connected_components(graph)
    elif algo_lower in ('floyd_warshall', 'fw'):
        res = floyd_warshall(graph)
    else:
        raise ValueError(f"Unknown network algorithm: {algorithm}")

    if log_result:
        log_algorithm_result(
            module='network',
            algorithm=res['algorithm'],
            execution_time_ms=res['execution_time_ms'],
            memory_kb=res['memory_kb'],
            solution_quality=100.0,
            input_size=graph.node_count,
        )

    return res


def compare_network_algorithms(start_node_id: int = 1) -> Dict[str, Any]:
    """Compare BFS, DFS, and Floyd-Warshall network metrics."""
    graph = load_network_graph()
    session_id = str(uuid.uuid4())

    b_res = bfs_traversal(graph, start_node_id)
    d_res = dfs_traversal(graph, start_node_id)
    fw_res = floyd_warshall(graph)

    for r in (b_res, d_res, fw_res):
        log_algorithm_result(
            module='network',
            algorithm=r['algorithm'],
            execution_time_ms=r['execution_time_ms'],
            memory_kb=r['memory_kb'],
            solution_quality=100.0,
            input_size=graph.node_count,
            session_id=session_id,
        )

    return {
        'session_id': session_id,
        'start_node_id': start_node_id,
        'node_count': graph.node_count,
        'edge_count': graph.edge_count // 2,
        'algorithms': {
            'bfs': b_res,
            'dfs': d_res,
            'floyd_warshall': fw_res,
        },
        'comparison_summary': [
            {
                'algorithm': 'BFS Traversal',
                'purpose': 'Level-order search & component analysis',
                'complexity': 'O(V + E)',
                'execution_time_ms': round(b_res['execution_time_ms'], 4),
            },
            {
                'algorithm': 'DFS Traversal',
                'purpose': 'Depth exploration & cycle detection',
                'complexity': 'O(V + E)',
                'execution_time_ms': round(d_res['execution_time_ms'], 4),
            },
            {
                'algorithm': 'Floyd-Warshall (APSP)',
                'purpose': 'All-pairs distance matrix computation',
                'complexity': 'O(V³)',
                'execution_time_ms': round(fw_res['execution_time_ms'], 4),
            },
        ]
    }
