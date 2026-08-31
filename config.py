"""
config.py
=========
Flask application configuration for MediRoute DSS.

Loads environment variables from .env file if present.
Environment variables override all defaults.

Usage:
    app.config.from_object(Config)

Required .env variables (copy from .env.example):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    """Base configuration — loaded from environment variables."""

    # ── Flask core ──
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'mediroute-dev-secret-change-in-production')
    DEBUG: bool = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    TESTING: bool = False

    # ── Application metadata ──
    APP_NAME: str = 'MediRoute DSS'
    APP_VERSION: str = '1.0.0'

    # ── Session ──
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=8)

    # ── Database (MySQL via PyMySQL) ──
    DB_HOST: str = os.environ.get('DB_HOST', 'localhost')
    DB_PORT: int = int(os.environ.get('DB_PORT', 3306))
    DB_USER: str = os.environ.get('DB_USER', 'root')
    DB_PASSWORD: str = os.environ.get('DB_PASSWORD', '')
    DB_NAME: str = os.environ.get('DB_NAME', 'mediroute')

    # ── Performance benchmarking ──
    # Minimum execution time (ms) to log to algorithm_results table.
    # Prevents logging trivial sub-microsecond calls.
    MIN_LOG_TIME_MS: float = float(os.environ.get('MIN_LOG_TIME_MS', '0.0'))

    # ── Scheduling constraint ──
    # Brute Force scheduler is O(n!) — safe only for small n.
    BRUTE_FORCE_MAX_N: int = int(os.environ.get('BRUTE_FORCE_MAX_N', '8'))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DB_NAME = os.environ.get('TEST_DB_NAME', 'mediroute_test')
    WTF_CSRF_ENABLED = False
