"""
routes/process_routes.py — Flask Data Processing Pipeline endpoints
"""

import uuid
import threading
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt

from database.db import db
from models.processed_feedback import ProcessedFeedback
from models.raw_feedback import RawFeedback
from services.processing_pipeline import ProcessingPipeline

process_bp = Blueprint("process_bp", __name__)

# Global thread-safe job tracking for processing pipeline runs
jobs_lock = threading.Lock()
jobs_db = {}

def background_processing_task(app, job_id: str, project_id: str):
    """
    Run pipeline processing in a background thread and update job status.
    """
    with jobs_lock:
        jobs_db[job_id]["status"] = "running"
        
    try:
        with app.app_context():
            pipeline = ProcessingPipeline()
            stats = pipeline.run(project_id=project_id)
            
            with jobs_lock:
                jobs_db[job_id].update({
                    "status": "completed",
                    "processed_count": stats["processed"],
                    "duplicate_count": stats["duplicates"],
                    "failed_count": stats["failed"],
                    "completed_at": str(uuid.uuid4())  # dummy timestamp surrogate
                })
    except Exception as e:
        with jobs_lock:
            jobs_db[job_id].update({
                "status": "failed",
                "error": str(e)
            })

@process_bp.route("/run", methods=["POST"])
@jwt_required()
def run_pipeline():
    claims = get_jwt()
    role = claims.get("role")
    
    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can run the processing pipeline."
        }), 403
        
    data = request.get_json() or {}
    project_id_str = data.get("project_id") or claims.get("project_id")
    
    project_id = None
    if project_id_str:
        try:
            project_id = uuid.UUID(project_id_str)
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid project_id format."
            }), 400
            
    # Count pending records first
    query = RawFeedback.query.filter_by(processing_status='pending')
    if project_id:
        query = query.filter_by(project_id=project_id)
    pending_count = query.count()
    
    if pending_count == 0:
        return jsonify({
            "success": True,
            "data": {
                "message": "No pending feedback records found to process.",
                "pending_count": 0
            }
        }), 200
        
    # Spawn background task
    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "started",
            "processed_count": 0,
            "duplicate_count": 0,
            "failed_count": 0,
            "error": None
        }
        
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=background_processing_task,
        args=(app, job_id, project_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "data": {
            "job_id": job_id,
            "status": "started",
            "pending_count": pending_count
        }
    }), 202


@process_bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def get_job_status(job_id):
    claims = get_jwt()
    role = claims.get("role")
    
    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view pipeline jobs."
        }), 403
        
    with jobs_lock:
        job = jobs_db.get(job_id)
        
    if not job:
        return jsonify({
            "success": False,
            "error": f"Job with ID {job_id} not found."
        }), 404
        
    return jsonify({
        "success": True,
        "data": job
    }), 200


@process_bp.route("/results", methods=["GET"])
@jwt_required()
def get_results():
    claims = get_jwt()
    role = claims.get("role")
    
    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view processed results."
        }), 403
        
    project_id_str = request.args.get("project_id") or claims.get("project_id")
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
        
    # Pagination
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except ValueError:
        page = 1
        page_size = 20
        
    # Query processed feedback
    query = ProcessedFeedback.query.filter_by(project_id=project_id)
    total = query.count()
    
    results = query.order_by(ProcessedFeedback.processing_timestamp.desc())\
                   .offset((page - 1) * page_size)\
                   .limit(page_size)\
                   .all()
                   
    serialized_results = [r.to_dict() for r in results]
    
    return jsonify({
        "success": True,
        "data": {
            "results": serialized_results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }), 200
