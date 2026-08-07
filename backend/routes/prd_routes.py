"""
routes/prd_routes.py — Flask Blueprint for Module 8 PRD Generator
"""

import logging
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt

logger = logging.getLogger(__name__)

prd_bp = Blueprint("prd_bp", __name__)


@prd_bp.route("/generate-prd", methods=["POST"])
@jwt_required()
def generate_prd():
    """Accept a feature name/ID and description, and generate a PRD using Gemini."""
    claims = get_jwt()
    role = claims.get("role")

    if role != "product_manager":
        return jsonify({
            "success": False,
            "error": "Forbidden: Only product managers can generate PRDs."
        }), 403

    data = request.get_json() or {}
    feature_name = data.get("feature_name", "").strip()
    description = data.get("description", "").strip()

    if not feature_name:
        return jsonify({
            "success": False,
            "error": "Missing feature name."
        }), 400

    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        # Return fallback heuristic PRD if API key is not available
        prd_text = (
            f"# PRD: {feature_name}\n\n"
            f"## 1. Problem Statement\n{description or 'No description provided.'}\n\n"
            f"## 2. Goals\n- Goal 1: Implement the feature efficiently.\n"
            f"- Goal 2: Meet user expectations based on feedback.\n\n"
            f"## 3. Functional Requirements\n- Requirement 1: User should be able to interact with the feature.\n"
            f"- Requirement 2: System should log usage statistics.\n\n"
            f"## 4. Non-Functional Requirements\n- Latency: Response time should be < 500ms.\n"
            f"- Security: Secure data transmission via HTTPS.\n\n"
            f"## 5. Risks & Mitigation\n- Risk: Potential delay in deployment. Mitigation: Agile sprints.\n\n"
            f"## 6. Success Metrics\n- Adoption rate > 50% in first month."
        )
    else:
        import urllib.request
        import json
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        prompt = f"""You are an expert product manager. Write a comprehensive Product Requirement Document (PRD) for the following feature.
Feature Name: {feature_name}
Description: {description}

Format the PRD using clean markdown with the following sections:
1. Executive Summary
2. Problem Statement & User Value
3. Goals & Out of Scope
4. Functional Requirements (list at least 3 detailed requirements)
5. Non-functional Requirements (performance, security, usability, etc.)
6. Risks & Mitigation Strategies
7. Success Metrics & KPIs

Do not include any other conversational text or markdown blocks besides the document markdown itself.
"""
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = json.loads(response.read().decode('utf-8'))
                prd_text = res_body["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as ex:
            logger.error("Gemini API call failed for PRD generation: %s", str(ex))
            return jsonify({
                "success": False,
                "error": "Failed to generate PRD using Gemini API.",
                "details": str(ex)
            }), 500

    return jsonify({
        "success": True,
        "prd": prd_text
    }), 200
