"""
auth/profile_routes.py — HTTP layer for profile view/update.

Kept as a separate blueprint (not merged into auth/routes.py) purely
for readability — registered under the same /api/auth prefix in
app.py, so the actual URL is /api/auth/profile either way.
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required
from auth.profile import view_profile, update_profile, ProfileError

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    user = request.current_user
    try:
        profile = view_profile(user["user_id"])
        return jsonify(profile), 200
    except ProfileError as e:
        return jsonify({"error": str(e)}), 409  # 409: integrity conflict, distinct from 404/403


@profile_bp.route("/profile", methods=["PUT"])
@login_required
def put_profile():
    user = request.current_user
    data = request.get_json(silent=True) or {}
    try:
        updated = update_profile(user["user_id"], data)
        return jsonify(updated), 200
    except ProfileError as e:
        return jsonify({"error": str(e)}), 409