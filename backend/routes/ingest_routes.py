"""
routes/ingest_routes.py — Flask Ingestion Service endpoints
"""

import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
import pandas as pd

from database.db import db
from services.ingestion_service import IngestionService
from models.user import User

ingest_bp = Blueprint("ingest_bp", __name__)

@ingest_bp.route("/csv", methods=["POST"])
@jwt_required()
def ingest_csv():
    claims = get_jwt()
    role = claims.get("role")
    
    # 1. Access Control
    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can upload CSV files."
        }), 403
        
    # 2. Check File
    if 'file' not in request.files:
        return jsonify({
            "success": False,
            "error": "No file uploaded. Form key must be 'file'."
        }), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "success": False,
            "error": "Empty filename."
        }), 400
        
    # 3. File validation
    is_valid_file, file_errors = IngestionService.validate_csv_file(file)
    if not is_valid_file:
        return jsonify({
            "success": False,
            "error": "File validation failed.",
            "details": file_errors
        }), 400
        
    # 4. Load with pandas
    try:
        df = pd.read_csv(file)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to read CSV file: {str(e)}"
        }), 400
        
    # 5. Schema validation
    is_valid_schema, missing_cols = IngestionService.validate_csv_schema(df)
    if not is_valid_schema:
        return jsonify({
            "success": False,
            "error": "Schema mismatch. Missing required columns.",
            "missing_columns": missing_cols
        }), 422
        
    # 6. Parse and store
    user_id = uuid.UUID(get_jwt_identity())
    project_id_str = request.form.get("project_id") or claims.get("project_id")
    
    if not project_id_str:
        return jsonify({
            "success": False,
            "error": "Missing project_id."
        }), 400
        
    try:
        project_id = uuid.UUID(project_id_str)
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid project_id format."
        }), 400
        
    batch_id = str(uuid.uuid4())
    valid_records, failed_rows = IngestionService.parse_csv_to_records(
        df=df,
        user_id=user_id,
        project_id=project_id,
        filename=file.filename,
        batch_id=batch_id
    )
    
    # Update IP and User Agent in metadata
    client_ip = request.remote_addr or "0.0.0.0"
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    for r in valid_records:
        r["raw_metadata"]["ip_address"] = client_ip
        r["raw_metadata"]["user_agent"] = user_agent
        
    # Store records
    ingested_count = 0
    if valid_records:
        try:
            ingested_count = IngestionService.store_raw_feedback(valid_records)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Database operation failed: {str(e)}"
            }), 503
            
    status_code = 201 if ingested_count > 0 else 200
    if failed_rows:
        status_code = 207  # Multi-Status (some rows failed)
        
    return jsonify({
        "success": True,
        "data": {
            "ingested_count": ingested_count,
            "failed_rows": failed_rows,
            "batch_id": batch_id
        }
    }), status_code


@ingest_bp.route("/feedback", methods=["POST"])
@jwt_required()
def ingest_feedback():
    claims = get_jwt()
    role = claims.get("role")
    user_id = uuid.UUID(get_jwt_identity())
    project_id_str = claims.get("project_id")
    
    if not project_id_str:
        # Fallback query if not in claims
        user = User.query.get(user_id)
        if user and user.project_id:
            project_id_str = str(user.project_id)
            
    if not project_id_str:
        return jsonify({
            "success": False,
            "error": "No project associated with this user."
        }), 400
        
    project_id = uuid.UUID(project_id_str)
    
    data = request.get_json() or {}
    
    subject = data.get("subject")
    description = data.get("description")
    
    if not subject or not description:
        return jsonify({
            "success": False,
            "error": "Missing required fields: subject and description."
        }), 400
        
    # Add client info
    data["ip_address"] = request.remote_addr or "0.0.0.0"
    data["user_agent"] = request.headers.get("User-Agent", "Unknown")
    
    record = IngestionService.parse_form_to_record(
        form_data=data,
        user_id=user_id,
        project_id=project_id,
        role=role
    )
    
    try:
        IngestionService.store_raw_feedback([record])
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to store feedback: {str(e)}"
        }), 500
        
    return jsonify({
        "success": True,
        "data": {
            "feedback_id": record["feedback_id"],
            "processing_status": "pending"
        }
    }), 201


@ingest_bp.route("/status/<feedback_id>", methods=["GET"])
@jwt_required()
def check_status(feedback_id):
    status_data = IngestionService.get_feedback_status(feedback_id)
    if not status_data:
        return jsonify({
            "success": False,
            "error": f"Feedback record with ID {feedback_id} not found."
        }), 404
        
    return jsonify({
        "success": True,
        "data": status_data
    }), 200
