"""
app.py — Flask application factory entrypoint
"""

import os
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from config import get_config
from database.db import db
from routes.auth_routes import auth_bp
from routes.ingest_routes import ingest_bp
from routes.process_routes import process_bp

def create_app(config_class=None):
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize Extensions
    db.init_app(app)
    
    jwt = JWTManager(app)
    
    # Configure CORS to allow frontend requests
    frontend_origin = app.config.get("FRONTEND_ORIGIN", "http://localhost:5173")
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}})
    
    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(ingest_bp, url_prefix="/api/ingest")
    app.register_blueprint(process_bp, url_prefix="/api/process")
    
    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": "Bad request",
            "details": str(error)
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "success": False,
            "error": "Unauthorized access token",
            "details": str(error)
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "success": False,
            "error": "Forbidden: Insufficient privileges",
            "details": str(error)
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "Resource not found",
            "details": str(error)
        }), 404

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({
            "success": False,
            "error": "Unprocessable entity schema mismatch",
            "details": str(error)
        }), 422

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            "success": False,
            "error": "Internal server error occurred",
            "details": str(error)
        }), 500
        
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({
            "success": False,
            "error": "Signature verification failed",
            "details": error_string
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": "Token has expired",
            "details": "Please log in again."
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({
            "success": False,
            "error": "Authorization header is missing",
            "details": error_string
        }), 401

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("FLASK_PORT", 5000))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=app.config.get("DEBUG", True))
