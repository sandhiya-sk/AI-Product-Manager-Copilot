"""
routes/__init__.py
"""
from .auth_routes import auth_bp
from .ingest_routes import ingest_bp
from .process_routes import process_bp

__all__ = ["auth_bp", "ingest_bp", "process_bp"]
