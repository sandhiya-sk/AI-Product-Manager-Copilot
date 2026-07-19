"""
routes/aggregate_routes.py — Module 5 Feature Request Aggregation endpoints

Provides REST API endpoints for running the aggregation pipeline,
polling job status, retrieving clustered results, and viewing summary stats.
"""

import uuid
import threading
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt

from database.db import db
from models.aggregated_feature import AggregatedFeature
from models.classified_feedback import ClassifiedFeedback
from services.aggregation_pipeline import AggregationPipeline

aggregate_bp = Blueprint("aggregate_bp", __name__)

# ──────────────────────────────────────────────────────────────
# Global thread-safe job tracking for aggregation pipeline runs
# ──────────────────────────────────────────────────────────────
aggregate_jobs_lock = threading.Lock()
aggregate_jobs_db = {}


def background_aggregation_task(app, job_id: str, project_id: str):
    """
    Run aggregation pipeline in a background thread and update job status.
    """
    with aggregate_jobs_lock:
        aggregate_jobs_db[job_id]["status"] = "running"

    try:
        with app.app_context():
            pipeline = AggregationPipeline()
            stats = pipeline.run(project_id=project_id)

            with aggregate_jobs_lock:
                aggregate_jobs_db[job_id].update({
                    "status": "completed",
                    "clusters_created": stats.get("clusters_created", 0),
                    "total_requests": stats.get("total_requests", 0),
                    "failed": stats.get("failed", 0),
                })
    except Exception as e:
        with aggregate_jobs_lock:
            aggregate_jobs_db[job_id].update({
                "status": "failed",
                "error": str(e),
            })


# ──────────────────────────────────────────────────────────────
# POST /api/aggregate/run — Trigger Aggregation Pipeline
# ──────────────────────────────────────────────────────────────

@aggregate_bp.route("/run", methods=["POST"])
@jwt_required()
def run_aggregation():
    """
    Trigger the Module 5 aggregation pipeline.
    Only product managers can run this.
    Spawns a background thread and returns a job_id for polling.
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can run the aggregation pipeline."
        }), 403

    data = request.get_json() or {}
    project_id_str = data.get("project_id") or claims.get("project_id")

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

    # Count feature requests available for aggregation
    feature_count = ClassifiedFeedback.query.filter_by(
        project_id=project_id,
        ai_category="Feature Request",
        classification_status="classified",
    ).count()

    if feature_count == 0:
        return jsonify({
            "success": True,
            "data": {
                "message": "No classified feature requests found to aggregate.",
                "feature_request_count": 0,
            }
        }), 200

    # Spawn background task
    job_id = str(uuid.uuid4())
    with aggregate_jobs_lock:
        aggregate_jobs_db[job_id] = {
            "job_id": job_id,
            "status": "started",
            "clusters_created": 0,
            "total_requests": 0,
            "failed": 0,
            "error": None,
        }

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=background_aggregation_task,
        args=(app, job_id, str(project_id)),
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "success": True,
        "data": {
            "job_id": job_id,
            "status": "started",
            "feature_request_count": feature_count,
        }
    }), 202


# ──────────────────────────────────────────────────────────────
# GET /api/aggregate/status/<job_id> — Poll Job Status
# ──────────────────────────────────────────────────────────────

@aggregate_bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def get_aggregation_status(job_id):
    """
    Check the status of a running aggregation job.
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view aggregation jobs."
        }), 403

    with aggregate_jobs_lock:
        job = aggregate_jobs_db.get(job_id)

    if not job:
        return jsonify({
            "success": False,
            "error": f"Aggregation job with ID {job_id} not found."
        }), 404

    return jsonify({
        "success": True,
        "data": job,
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/aggregate/clusters — Paginated Cluster List
# ──────────────────────────────────────────────────────────────

@aggregate_bp.route("/clusters", methods=["GET"])
@jwt_required()
def get_clusters():
    """
    Retrieve paginated aggregated feature clusters with optional filters.

    Query params:
      - project_id (required)
      - page (default: 1)
      - page_size (default: 20)
      - importance (optional filter: Critical/High/Medium/Low)
      - trend (optional filter: rising/stable/declining)
      - sort_by (optional: frequency/importance/affected_users/trend, default: frequency)
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view aggregated features."
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
    query = AggregatedFeature.query.filter_by(
        project_id=project_id,
        aggregation_status="aggregated",
    )

    # Optional filters
    importance_filter = request.args.get("importance")
    if importance_filter:
        query = query.filter_by(importance=importance_filter)

    trend_filter = request.args.get("trend")
    if trend_filter:
        query = query.filter_by(trend_direction=trend_filter)

    total = query.count()

    # Sorting
    sort_by = request.args.get("sort_by", "frequency")
    if sort_by == "importance":
        # Custom order: Critical > High > Medium > Low
        from sqlalchemy import case
        importance_order = case(
            {"Critical": 0, "High": 1, "Medium": 2, "Low": 3},
            value=AggregatedFeature.importance,
            else_=4,
        )
        query = query.order_by(importance_order, AggregatedFeature.frequency.desc())
    elif sort_by == "affected_users":
        query = query.order_by(AggregatedFeature.affected_users.desc())
    elif sort_by == "trend":
        query = query.order_by(AggregatedFeature.trend_direction.asc(), AggregatedFeature.frequency.desc())
    else:  # Default: frequency
        query = query.order_by(AggregatedFeature.frequency.desc())

    results = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return jsonify({
        "success": True,
        "data": {
            "clusters": [r.to_dict() for r in results],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/aggregate/clusters/<aggregate_id> — Single Cluster Detail
# ──────────────────────────────────────────────────────────────

@aggregate_bp.route("/clusters/<aggregate_id>", methods=["GET"])
@jwt_required()
def get_cluster_detail(aggregate_id):
    """
    Retrieve a single aggregated feature cluster with full details,
    including member feedback records.
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view cluster details."
        }), 403

    try:
        agg_uuid = uuid.UUID(aggregate_id)
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid aggregate_id format."
        }), 400

    cluster = AggregatedFeature.query.get(agg_uuid)
    if not cluster:
        return jsonify({
            "success": False,
            "error": f"Cluster with ID {aggregate_id} not found."
        }), 404

    cluster_dict = cluster.to_dict()

    # Fetch sample member feedback details
    sample_ids = cluster.sample_feedback_ids or []
    sample_feedbacks = []
    if sample_ids:
        sample_records = ClassifiedFeedback.query.filter(
            ClassifiedFeedback.classified_id.in_(sample_ids)
        ).all()
        for rec in sample_records:
            fb_dict = {
                "classified_id": str(rec.classified_id),
                "ai_summary": rec.ai_summary,
                "ai_sentiment": rec.ai_sentiment,
                "keywords": rec.keywords or [],
                "weight": rec.weight,
            }
            if rec.processed_feedback:
                fb_dict["original_subject"] = rec.processed_feedback.original_subject
                fb_dict["original_description"] = rec.processed_feedback.original_description
            sample_feedbacks.append(fb_dict)

    cluster_dict["sample_feedbacks"] = sample_feedbacks

    return jsonify({
        "success": True,
        "data": cluster_dict,
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/aggregate/stats — Aggregation Summary Statistics
# ──────────────────────────────────────────────────────────────

@aggregate_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_aggregation_stats():
    """
    Retrieve summary statistics for aggregated feature clusters:
    - Total clusters
    - Total feature requests aggregated
    - Importance distribution
    - Trend distribution
    - Top clusters by frequency
    - Total affected users
    """
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can view aggregation statistics."
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

    # Fetch all aggregated clusters for this project
    clusters = AggregatedFeature.query.filter_by(
        project_id=project_id,
        aggregation_status="aggregated",
    ).all()

    if not clusters:
        return jsonify({
            "success": True,
            "data": {
                "total_clusters": 0,
                "total_feature_requests": 0,
                "total_affected_users": 0,
                "importance_distribution": {},
                "trend_distribution": {},
                "top_clusters": [],
                "sentiment_breakdown": {},
            }
        }), 200

    # Calculate distributions
    importance_dist = {}
    trend_dist = {}
    sentiment_dist = {}
    total_requests = 0
    all_user_count = 0

    for c in clusters:
        # Importance
        importance_dist[c.importance] = importance_dist.get(c.importance, 0) + 1

        # Trend
        trend_dist[c.trend_direction] = trend_dist.get(c.trend_direction, 0) + 1

        # Sentiment
        sentiment_dist[c.dominant_sentiment] = sentiment_dist.get(c.dominant_sentiment, 0) + 1

        total_requests += c.frequency
        all_user_count += c.affected_users

    # Top clusters by frequency (top 10)
    sorted_clusters = sorted(clusters, key=lambda x: x.frequency, reverse=True)
    top_clusters = [
        {
            "cluster_label": c.cluster_label,
            "frequency": c.frequency,
            "importance": c.importance,
            "affected_users": c.affected_users,
            "trend_direction": c.trend_direction,
        }
        for c in sorted_clusters[:10]
    ]

    return jsonify({
        "success": True,
        "data": {
            "total_clusters": len(clusters),
            "total_feature_requests": total_requests,
            "total_affected_users": all_user_count,
            "importance_distribution": importance_dist,
            "trend_distribution": trend_dist,
            "top_clusters": top_clusters,
            "sentiment_breakdown": sentiment_dist,
        }
    }), 200
