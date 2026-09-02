"""
routes/lab_routes.py
====================
Algorithm Lab route — interactive sandbox for experimenting with algorithms.

Route:
  GET /algorithm-lab — Interactive sandbox for selecting nodes, weights, parameters.
"""

import logging
from flask import Blueprint, render_template

from routes.auth_routes import login_required
from database.db import query_db

logger = logging.getLogger(__name__)

lab_bp = Blueprint('lab', __name__)


@lab_bp.route('/algorithm-lab')
@login_required
def algorithm_lab():
    """Interactive Algorithm Lab page."""
    locations = query_db("SELECT id, name, location_type FROM locations ORDER BY name") or []
    hospitals = query_db("SELECT id, name FROM hospitals ORDER BY name") or []
    patients = query_db("SELECT id, name, emergency_level FROM patients ORDER BY name LIMIT 20") or []

    return render_template(
        'lab/index.html',
        locations=locations,
        hospitals=hospitals,
        patients=patients,
    )
