"""
routes/pages_routes.py
======================
Informational pages: About, Complexity Analysis, Test Results.

Routes:
  GET /about               — Project overview & academic background
  GET /complexity-analysis — Big-O time & space complexity reference table
  GET /test-results        — System validation & pytest execution log
"""

import logging
from flask import Blueprint, render_template

from routes.auth_routes import login_required

logger = logging.getLogger(__name__)

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/about')
@login_required
def about():
    return render_template('pages/about.html')


@pages_bp.route('/complexity-analysis')
@login_required
def complexity_analysis():
    return render_template('pages/complexity.html')


@pages_bp.route('/test-results')
@login_required
def test_results():
    return render_template('pages/test_results.html')
