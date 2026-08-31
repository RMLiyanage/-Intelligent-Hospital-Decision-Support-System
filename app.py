"""
app.py
======
MediRoute Flask application factory.

Usage:
    flask run                       # Development server (uses FLASK_APP=app.py)
    python app.py                   # Direct run

The application factory pattern (create_app) allows:
  - Different configurations for testing vs production
  - Clean blueprint registration
  - Proper teardown of database connections

Architecture:
    Request → Blueprint Route → Service Layer → Algorithm → Data Structure → DB
"""

import logging
from flask import Flask, jsonify, render_template

from config import Config
from database.db import init_app as init_db


def create_app(config_class=None):
    """
    Flask application factory.

    Parameters
    ----------
    config_class : Config class to use (defaults to Config from config.py)

    Returns
    -------
    Flask : Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class or Config)

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if app.config['DEBUG'] else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # -------------------------------------------------------- #
    # Database teardown                                        #
    # -------------------------------------------------------- #
    init_db(app)

    # -------------------------------------------------------- #
    # Register Blueprints                                      #
    # -------------------------------------------------------- #
    from routes.auth_routes import auth_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.hospital_routes import hospital_bp
    from routes.patient_routes import patient_bp
    from routes.emergency_routes import emergency_bp
    from routes.algorithm_routes import algo_api_bp
    from routes.performance_routes import performance_bp
    from routes.lab_routes import lab_bp
    from routes.pages_routes import pages_bp
    from routes.doctor_routes import doctor_bp
    from routes.report_routes import reports_bp
    from routes.user_routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(hospital_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(algo_api_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(lab_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(user_bp)


    @app.template_filter('time_fmt')
    def time_fmt(val, default='00:00'):
        if val is None or val == '':
            return default
        try:
            s = str(val)
            parts = s.split(':')
            if len(parts) >= 2:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            return s[:5]
        except Exception:
            return str(val)

    # -------------------------------------------------------- #
    # Health check endpoint                                    #
    # -------------------------------------------------------- #
    @app.route('/health')
    def health():
        """
        Simple health check endpoint.
        Returns 200 if the app is running.
        Database connectivity is NOT checked here (call /api/status for that).
        """
        return jsonify({
            'status': 'ok',
            'app': app.config.get('APP_NAME', 'MediRoute DSS'),
            'version': app.config.get('APP_VERSION', '1.0.0'),
        }), 200

    @app.route('/api/status')
    def db_status():
        """Check database connectivity."""
        try:
            from database.db import query_db
            result = query_db('SELECT 1 AS alive', one=True)
            return jsonify({'status': 'ok', 'database': 'connected'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'database': str(e)}), 503

    # -------------------------------------------------------- #
    # Error handlers                                           #
    # -------------------------------------------------------- #
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error("500 error: %s", e)
        return render_template('errors/500.html'), 500

    # -------------------------------------------------------- #
    # Context processors (available in all templates)          #
    # -------------------------------------------------------- #
    @app.context_processor
    def inject_globals():
        from flask import session
        return {
            'app_name': app.config.get('APP_NAME', 'MediRoute DSS'),
            'app_version': app.config.get('APP_VERSION', '1.0.0'),
            'current_user': {
                'id':    session.get('user_id'),
                'name':  session.get('user_name', ''),
                'email': session.get('user_email', ''),
                'role':  session.get('role', ''),
            },
        }

    app.logger.info("MediRoute DSS started — debug=%s", app.config['DEBUG'])
    return app


# -------------------------------------------------------- #
# Direct run entry point                                   #
# -------------------------------------------------------- #
if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, host='0.0.0.0', port=5000)
