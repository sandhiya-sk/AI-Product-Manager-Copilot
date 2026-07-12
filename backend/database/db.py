"""
database/db.py — SQLAlchemy engine and session setup
"""

from flask_sqlalchemy import SQLAlchemy

# Single shared SQLAlchemy instance imported by all models and services
db = SQLAlchemy()
