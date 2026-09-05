"""
auth/middleware.py — Authentication + RBAC middleware.

Section 8 of the requirements: RBAC must be enforced server-side.
These decorators are meant to be imported and reused by EVERY
teammate's routes (Tahmid's events, Pallab's tickets/admin), not just
your own — this is the shared enforcement layer for the whole app.

Usage:
    @app.route("/api/events", methods=["POST"])
    @login_required
    @role_required("SELLER")
    def create_event():
        user = request.current_user  # set by login_required
        ...
"""

from functools import wraps
from flask import request, jsonify
from auth.sessions import get_session


def login_required(f):
    """
    Requires a valid, non-expired session token in the
    Authorization header: "Authorization: Bearer <token>"

    On success, attaches the session dict to request.current_user
    so the route handler can access user_id / role without doing
    its own lookup.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        session = get_session(token)
        if session is None:
            return jsonify({"error": "Session invalid or expired"}), 401

        request.current_user = session  # {"user_id": ..., "role": ..., ...}
        return f(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """
    Restricts a route to specific roles. Must be used AFTER
    @login_required (so request.current_user already exists).

    Example: @role_required("ADMIN") or @role_required("SELLER", "ADMIN")
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if user is None:
                return jsonify({"error": "Authentication required"}), 401
            if user["role"] not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator