"""
routes/auth_routes.py — Flask authentication routing
"""

import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt

from database.db import db
from models.user import User

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    full_name = data.get("full_name")
    project_id_str = data.get("project_id")
    
    if not email or not password or not role:
        return jsonify({
            "success": False,
            "error": "Missing required fields: email, password, and role are required."
        }), 400
        
    if role not in ("product_manager", "customer"):
        return jsonify({
            "success": False,
            "error": "Invalid role. Role must be 'product_manager' or 'customer'."
        }), 400
        
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({
            "success": False,
            "error": "Email is already registered."
        }), 409
        
    # Hash password using bcrypt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    # Process optional project_id
    project_uuid = None
    if project_id_str:
        try:
            project_uuid = uuid.UUID(project_id_str)
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid project_id format. Must be a valid UUID."
            }), 400
    else:
        # Generate a project ID if not provided, just for onboarding purposes
        project_uuid = uuid.uuid4()
            
    try:
        new_user = User(
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role=role,
            project_id=project_uuid,
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "user_id": str(new_user.user_id),
                "message": "Registration successful"
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"An error occurred during registration: {str(e)}"
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Missing email or password."
        }), 400
        
    user = User.query.filter_by(email=email, is_active=True).first()
    if not user:
        return jsonify({
            "success": False,
            "error": "Invalid credentials."
        }), 401
        
    # Verify password
    password_bytes = password.encode('utf-8')
    hash_bytes = user.password_hash.encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, hash_bytes):
        return jsonify({
            "success": False,
            "error": "Invalid credentials."
        }), 401
        
    # Generate JWT Token with claims
    additional_claims = {
        "role": user.role,
        "project_id": str(user.project_id) if user.project_id else None,
        "full_name": user.full_name
    }
    
    access_token = create_access_token(
        identity=str(user.user_id),
        additional_claims=additional_claims
    )
    
    return jsonify({
        "success": True,
        "data": {
            "access_token": access_token,
            "user_id": str(user.user_id),
            "role": user.role,
            "project_id": str(user.project_id) if user.project_id else None
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(uuid.UUID(user_id))
    if not user or not user.is_active:
        return jsonify({
            "success": False,
            "error": "User not found or inactive."
        }), 404
        
    return jsonify({
        "success": True,
        "data": user.to_dict()
    }), 200
