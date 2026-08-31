"""
algorithms package
==================
MediRoute Pure Python Algorithms for 5 Core Modules.

Exports
-------
Module 1: Route Optimization
  - astar                   (Primary: A* with Haversine heuristic)
  - dijkstra                (Comparison: Dijkstra's Algorithm)
  - bfs_shortest_path       (Comparison: BFS unweighted shortest path)

Module 2: Resource Allocation
  - greedy_allocation       (Primary: Greedy priority allocation)
  - hungarian_allocation    (Comparison: Hungarian Kuhn-Munkres algorithm)

Module 3: Network Analysis
  - bfs_traversal           (Level-order traversal)
  - dfs_traversal           (Depth-first traversal)
  - find_connected_components (Network partition analysis)
  - floyd_warshall          (Primary: All-pairs shortest path)

Module 4: Intelligent Decision Support
  - weighted_ranking        (Primary: Multi-criteria decision analysis)
  - decision_tree_recommendation (Comparison: Rule-based classification)

Module 5: Scheduling Optimization
  - greedy_scheduler        (Baseline: Earliest deadline first)
  - genetic_algorithm_scheduler (Primary: Metaheuristic evolution)
  - brute_force_scheduler   (Exact comparison: O(N!) capped at N <= 8)
"""

from algorithms.route.astar import astar
from algorithms.route.dijkstra import dijkstra
from algorithms.route.bfs_route import bfs_shortest_path

from algorithms.allocation.greedy_allocation import greedy_allocation
from algorithms.allocation.hungarian import hungarian_allocation

from algorithms.network.bfs_dfs import bfs_traversal, dfs_traversal, find_connected_components
from algorithms.network.floyd_warshall import floyd_warshall, reconstruct_fw_path

from algorithms.decision.weighted_ranking import weighted_ranking
from algorithms.decision.decision_tree import decision_tree_recommendation

from algorithms.scheduling.greedy_scheduler import greedy_scheduler
from algorithms.scheduling.genetic_algorithm import genetic_algorithm_scheduler
from algorithms.scheduling.brute_force_scheduler import brute_force_scheduler

__all__ = [
    # Module 1
    'astar', 'dijkstra', 'bfs_shortest_path',
    # Module 2
    'greedy_allocation', 'hungarian_allocation',
    # Module 3
    'bfs_traversal', 'dfs_traversal', 'find_connected_components',
    'floyd_warshall', 'reconstruct_fw_path',
    # Module 4
    'weighted_ranking', 'decision_tree_recommendation',
    # Module 5
    'greedy_scheduler', 'genetic_algorithm_scheduler', 'brute_force_scheduler',
]
