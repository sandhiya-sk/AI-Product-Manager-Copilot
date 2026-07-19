"""
routes/classify_routes.py — Module 4 NLP Classification & Theme Extraction endpoints

Provides REST API endpoints for running the classification pipeline,
polling job status, retrieving classified results, and viewing aggregated stats.
"""

import uuid
import threading
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt

from database.db import db
from models.processed_feedback import ProcessedFeedback
from models.classified_feedback import ClassifiedFeedback
from services.classification_pipeline import ClassificationPipeline

classify_bp = Blueprint("classify_bp", __name__)

# ──────────────────────────────────────────────────────────────
# Global thread-safe job tracking for classification pipeline runs
# ──────────────────────────────────────────────────────────────
classify_jobs_lock = threading.Lock()
classify_jobs_db = {}


def background_classification_task(app, job_id: str, project_id: str):
    """
    Run classification pipeline in a background thread and update job status.
    """
    with classify_jobs_lock:
        classify_jobs_db[job_id]["status"] = "running"

    try:
        with app.app_context():
            pipeline = ClassificationPipeline()
            stats = pipeline.run(project_id=project_id)

            with classify_jobs_lock:
                classify_jobs_db[job_id].update({
                    "status": "completed",
                    "classified_count": stats["classified"],
                    "failed_count": stats["failed"],
                    "total_fetched": stats["total_fetched"],
                })
    except Exception as e:
        with classify_jobs_lock:
            classify_jobs_db[job_id].update({
                "status": "failed",
                "error": str(e),
            })


# ──────────────────────────────────────────────────────────────
# POST /api/classify/run — Trigger Classification Pipeline
# ──────────────────────────────────────────────────────────────

@classify_bp.route("/run", methods=["POST"])
@jwt_required()
def run_classification():
    """
    Trigger the Module 4 classification pipeline.
    Only product managers can run this.
    Spawns a background thread and returns a job_id for polling.
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can run the classification pipeline."
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

    # Count unclassified records
    query = ProcessedFeedback.query.filter_by(
        ready_for_classification=True
    ).filter(ProcessedFeedback.classified_at.is_(None))

    if project_id:
        query = query.filter_by(project_id=project_id)

    unclassified_count = query.count()

    if unclassified_count == 0:
        return jsonify({
            "success": True,
            "data": {
                "message": "No unclassified feedback records found.",
                "unclassified_count": 0,
            }
        }), 200

    # Spawn background task
    job_id = str(uuid.uuid4())
    with classify_jobs_lock:
        classify_jobs_db[job_id] = {
            "job_id": job_id,
            "status": "started",
            "classified_count": 0,
            "failed_count": 0,
            "total_fetched": 0,
            "error": None,
        }

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=background_classification_task,
        args=(app, job_id, project_id),
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "success": True,
        "data": {
            "job_id": job_id,
            "status": "started",
            "unclassified_count": unclassified_count,
        }
    }), 202


# ──────────────────────────────────────────────────────────────
# GET /api/classify/status/<job_id> — Poll Job Status
# ──────────────────────────────────────────────────────────────

@classify_bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def get_classification_status(job_id):
    """
    Check the status of a running classification job.
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view classification jobs."
        }), 403

    with classify_jobs_lock:
        job = classify_jobs_db.get(job_id)

    if not job:
        return jsonify({
            "success": False,
            "error": f"Classification job with ID {job_id} not found."
        }), 404

    return jsonify({
        "success": True,
        "data": job,
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/classify/results — Paginated Classified Results
# ──────────────────────────────────────────────────────────────

@classify_bp.route("/results", methods=["GET"])
@jwt_required()
def get_classification_results():
    """
    Retrieve paginated classified feedback results with optional filters.

    Query params:
      - project_id (required)
      - page (default: 1)
      - page_size (default: 20)
      - category (optional filter)
      - sentiment (optional filter)
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view classified results."
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

    # Build query
    query = ClassifiedFeedback.query.filter_by(project_id=project_id)

    # Optional filters
    category_filter = request.args.get("category")
    if category_filter:
        query = query.filter_by(ai_category=category_filter)

    sentiment_filter = request.args.get("sentiment")
    if sentiment_filter:
        query = query.filter_by(ai_sentiment=sentiment_filter)

    total = query.count()

    results = (
        query.order_by(ClassifiedFeedback.classified_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Join with processed_feedback for original text context
    serialized = []
    for clf in results:
        clf_dict = clf.to_dict()
        # Attach original feedback text for display
        if clf.processed_feedback:
            clf_dict["original_subject"] = clf.processed_feedback.original_subject
            clf_dict["original_description"] = clf.processed_feedback.original_description
            clf_dict["clean_text"] = clf.processed_feedback.clean_text
        serialized.append(clf_dict)

    return jsonify({
        "success": True,
        "data": {
            "results": serialized,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/classify/results/<classified_id> — Single Result Detail
# ──────────────────────────────────────────────────────────────

@classify_bp.route("/results/<classified_id>", methods=["GET"])
@jwt_required()
def get_classification_detail(classified_id):
    """
    Retrieve a single classified feedback record with full details.
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view classification details."
        }), 403

    try:
        clf_uuid = uuid.UUID(classified_id)
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid classified_id format."
        }), 400

    clf = ClassifiedFeedback.query.get(clf_uuid)
    if not clf:
        return jsonify({
            "success": False,
            "error": f"Classified feedback with ID {classified_id} not found."
        }), 404

    clf_dict = clf.to_dict()
    # Attach source feedback for full context
    if clf.processed_feedback:
        clf_dict["original_subject"] = clf.processed_feedback.original_subject
        clf_dict["original_description"] = clf.processed_feedback.original_description
        clf_dict["clean_text"] = clf.processed_feedback.clean_text
        clf_dict["standardized_text"] = clf.processed_feedback.standardized_text
        clf_dict["tokens"] = clf.processed_feedback.tokens or []
        clf_dict["lemmas"] = clf.processed_feedback.lemmas or []
        clf_dict["priority"] = clf.processed_feedback.priority
        clf_dict["source"] = clf.processed_feedback.source
        clf_dict["submitted_by_role"] = clf.processed_feedback.submitted_by_role

    return jsonify({
        "success": True,
        "data": clf_dict,
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/classify/stats — Aggregated Classification Statistics
# ──────────────────────────────────────────────────────────────

@classify_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_classification_stats():
    """
    Retrieve aggregated statistics:
    - Category distribution (counts)
    - Sentiment distribution (counts)
    - Top keywords (frequency)
    - Top themes (frequency)
    - Top pain points (frequency)
    - Average confidence score
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view classification statistics."
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

    # Fetch all classified records for this project
    records = ClassifiedFeedback.query.filter_by(
        project_id=project_id,
        classification_status="classified",
    ).all()

    if not records:
        return jsonify({
            "success": True,
            "data": {
                "total_classified": 0,
                "category_distribution": {},
                "sentiment_distribution": {},
                "top_keywords": [],
                "top_themes": [],
                "top_pain_points": [],
                "avg_confidence_score": 0.0,
                "total_weighted_submissions": 0,
            }
        }), 200

    # Category distribution (weighted)
    category_dist = {}
    sentiment_dist = {}
    keyword_freq = {}
    theme_freq = {}
    pain_point_freq = {}
    total_confidence = 0.0
    total_weight = 0

    for rec in records:
        w = rec.weight or 1

        # Category
        cat = rec.ai_category
        category_dist[cat] = category_dist.get(cat, 0) + w

        # Sentiment
        sent = rec.ai_sentiment
        sentiment_dist[sent] = sentiment_dist.get(sent, 0) + w

        # Keywords
        for kw in (rec.keywords or []):
            kw_lower = kw.lower().strip()
            if kw_lower:
                keyword_freq[kw_lower] = keyword_freq.get(kw_lower, 0) + w

        # Themes
        for th in (rec.themes or []):
            th_lower = th.lower().strip()
            if th_lower:
                theme_freq[th_lower] = theme_freq.get(th_lower, 0) + w

        # Pain points
        for pp in (rec.pain_points or []):
            pp_lower = pp.lower().strip()
            if pp_lower:
                pain_point_freq[pp_lower] = pain_point_freq.get(pp_lower, 0) + w

        total_confidence += rec.ai_confidence_score
        total_weight += w

    # Sort and take top N
    top_keywords = sorted(
        keyword_freq.items(), key=lambda x: x[1], reverse=True
    )[:20]
    top_themes = sorted(
        theme_freq.items(), key=lambda x: x[1], reverse=True
    )[:15]
    top_pain_points = sorted(
        pain_point_freq.items(), key=lambda x: x[1], reverse=True
    )[:15]

    avg_confidence = (
        total_confidence / len(records) if records else 0.0
    )

    return jsonify({
        "success": True,
        "data": {
            "total_classified": len(records),
            "category_distribution": category_dist,
            "sentiment_distribution": sentiment_dist,
            "top_keywords": [
                {"keyword": kw, "count": ct} for kw, ct in top_keywords
            ],
            "top_themes": [
                {"theme": th, "count": ct} for th, ct in top_themes
            ],
            "top_pain_points": [
                {"pain_point": pp, "count": ct} for pp, ct in top_pain_points
            ],
            "avg_confidence_score": round(avg_confidence, 3),
            "total_weighted_submissions": total_weight,
        }
    }), 200
