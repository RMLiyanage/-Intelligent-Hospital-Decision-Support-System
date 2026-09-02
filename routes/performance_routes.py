"""
routes/performance_routes.py
=============================
Performance Dashboard & Comparative Evaluation routes.

Routes:
  GET /performance — Experimental benchmark stats & execution time charts
  GET /algorithm-comparison — Side-by-side comparison tables across all 5 modules
  GET /api/performance/chart — Benchmark data JSON for Chart.js
"""

import logging
from flask import Blueprint, render_template, jsonify

from routes.auth_routes import login_required
from services.performance_service import get_recent_results, get_comparison_summary_by_module

logger = logging.getLogger(__name__)

performance_bp = Blueprint('performance', __name__)


@performance_bp.route('/performance')
@login_required
def performance_dashboard():
    """Performance & experimental evaluation dashboard."""
    recent_runs = get_recent_results(limit=30)
    route_stats = get_comparison_summary_by_module('route')
    alloc_stats = get_comparison_summary_by_module('allocation')
    net_stats = get_comparison_summary_by_module('network')
    dec_stats = get_comparison_summary_by_module('decision')
    sched_stats = get_comparison_summary_by_module('scheduling')

    return render_template(
        'performance/index.html',
        recent_runs=recent_runs,
        route_stats=route_stats,
        alloc_stats=alloc_stats,
        net_stats=net_stats,
        dec_stats=dec_stats,
        sched_stats=sched_stats,
    )


@performance_bp.route('/algorithm-comparison')
@login_required
def algorithm_comparison():
    """Comprehensive side-by-side algorithm comparison page."""
    return render_template('performance/comparison.html')


@performance_bp.route('/api/performance/chart')
@login_required
def performance_chart_data():
    """Return JSON dataset for Chart.js performance graphs."""
    modules = ['route', 'allocation', 'network', 'decision', 'scheduling']
    data = {}
    for m in modules:
        data[m] = get_comparison_summary_by_module(m)
    return jsonify(data)
