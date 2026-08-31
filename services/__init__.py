"""
services package
================
MediRoute Service Layer bridging Flask route controllers with pure Python algorithm implementations.
"""

from services.performance_service import log_algorithm_result, get_recent_results, get_comparison_summary_by_module
from services.route_service import find_optimal_route, compare_route_algorithms
from services.allocation_service import run_resource_allocation, compare_allocation_algorithms
from services.network_service import run_network_analysis, compare_network_algorithms
from services.decision_service import recommend_hospital, compare_decision_algorithms
from services.scheduling_service import optimize_schedule, compare_scheduling_algorithms
from services.emergency_service import process_emergency_pipeline

__all__ = [
    'log_algorithm_result', 'get_recent_results', 'get_comparison_summary_by_module',
    'find_optimal_route', 'compare_route_algorithms',
    'run_resource_allocation', 'compare_allocation_algorithms',
    'run_network_analysis', 'compare_network_algorithms',
    'recommend_hospital', 'compare_decision_algorithms',
    'optimize_schedule', 'compare_scheduling_algorithms',
    'process_emergency_pipeline',
]
