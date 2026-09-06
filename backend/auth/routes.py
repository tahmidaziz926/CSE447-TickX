"""
auth/routes.py — HTTP layer for authentication.

Registers a Flask Blueprint so app.py can do:
    from auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

Endpoints:
    POST /api/auth/register      -> create a buyer/seller account
    POST /api/auth/login         -> step 1: password check, sends OTP
    POST /api/auth/otp/verify    -> step 2: OTP check, returns session token
    POST /api/auth/logout        -> invalidate session
    GET  /api/auth/me            -> example protected route
"""

from flask import Blueprint, request, jsonify
from auth.services import (
    register_user, login_step1_password, login_step2_otp, logout_user, AuthError
)
from auth.middleware import login_required


auth_bp = Blueprint("auth", __name__)



@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "").strip().upper()
    personal_info = data.get("personal_info", {})  # {"name":..., "phone":..., "address":...}

    try:
        result = register_user(email, password, role, personal_info)
        return jsonify(result), 201
    except AuthError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    try:
        result = login_step1_password(email, password)
        return jsonify(result), 200
    except AuthError as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/otp/verify", methods=["POST"])
def otp_verify():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "")
    code = data.get("code", "")

    try:
        result = login_step2_otp(user_id, code)
        return jsonify(result), 200
    except AuthError as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ", 1)[1]
    logout_user(token)
    return jsonify({"message": "logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Example protected route — confirms the auth flow works end to end."""
    user = request.current_user
    return jsonify({
        "user_id": str(user["user_id"]),
        "role": user["role"],
    }), 200