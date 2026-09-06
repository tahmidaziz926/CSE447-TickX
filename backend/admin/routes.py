"""
admin/routes.py — HTTP layer for the admin dashboard.
Every route requires ADMIN role.
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required, role_required
from admin.services import (
    list_users, list_pending_sellers, approve_seller, reject_seller,
    suspend_account, reactivate_account, list_all_events,
    admin_deactivate_event, security_logs, AdminError,
)
from keys.service import list_keys_for_admin, rotate_key, revoke_key, KeyLifecycleError
from tickets.models import transactions_collection

from auth.models import get_pending_sellers, update_seller_status
from security_logs import log_security_event


admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/sellers/pending", methods=["GET"])
@login_required
def list_pending_sellers():
    if request.current_user["role"] != "ADMIN":
        return jsonify({"error": "forbidden"}), 403

    sellers = get_pending_sellers()
    return jsonify([
        {
            "user_id": str(s["_id"]),
            "email": s["email"],
            "personal_info": s.get("personal_info", {}),
        }
        for s in sellers
    ]), 200


@admin_bp.route("/sellers/<user_id>/approve", methods=["POST"])
@login_required
def approve_seller(user_id):
    if request.current_user["role"] != "ADMIN":
        return jsonify({"error": "forbidden"}), 403

    success = update_seller_status(user_id, "APPROVED")
    if not success:
        return jsonify({"error": "seller not found or already processed"}), 404

    log_security_event(
        "SELLER_APPROVED",
        f"Seller {user_id} approved by admin",
        {"user_id": user_id, "admin_id": str(request.current_user["user_id"])},
    )
    return jsonify({"user_id": user_id, "status": "APPROVED"}), 200


@admin_bp.route("/sellers/<user_id>/reject", methods=["POST"])
@login_required
def reject_seller(user_id):
    if request.current_user["role"] != "ADMIN":
        return jsonify({"error": "forbidden"}), 403

    success = update_seller_status(user_id, "REJECTED")
    if not success:
        return jsonify({"error": "seller not found or already processed"}), 404

    log_security_event(
        "SELLER_REJECTED",
        f"Seller {user_id} rejected by admin",
        {"user_id": user_id, "admin_id": str(request.current_user["user_id"])},
    )
    return jsonify({"user_id": user_id, "status": "REJECTED"}), 200

@admin_bp.route("/users", methods=["GET"])
@login_required
@role_required("ADMIN")
def users():
    return jsonify(list_users(request.args.get("role"))), 200


@admin_bp.route("/sellers/pending", methods=["GET"])
@login_required
@role_required("ADMIN")
def pending_sellers():
    return jsonify(list_pending_sellers()), 200


@admin_bp.route("/sellers/<seller_id>/approve", methods=["POST"])
@login_required
@role_required("ADMIN")
def approve(seller_id):
    admin = request.current_user
    try:
        approve_seller(seller_id, admin["user_id"])
        return jsonify({"seller_id": seller_id, "seller_status": "APPROVED"}), 200
    except AdminError as e:
        return jsonify({"error": str(e)}), 404


@admin_bp.route("/sellers/<seller_id>/reject", methods=["POST"])
@login_required
@role_required("ADMIN")
def reject(seller_id):
    admin = request.current_user
    try:
        reject_seller(seller_id, admin["user_id"])
        return jsonify({"seller_id": seller_id, "seller_status": "REJECTED"}), 200
    except AdminError as e:
        return jsonify({"error": str(e)}), 404


@admin_bp.route("/users/<user_id>/suspend", methods=["POST"])
@login_required
@role_required("ADMIN")
def suspend(user_id):
    admin = request.current_user
    try:
        suspend_account(user_id, admin["user_id"])
        return jsonify({"user_id": user_id, "account_status": "SUSPENDED"}), 200
    except AdminError as e:
        return jsonify({"error": str(e)}), 404


@admin_bp.route("/users/<user_id>/reactivate", methods=["POST"])
@login_required
@role_required("ADMIN")
def reactivate(user_id):
    admin = request.current_user
    try:
        reactivate_account(user_id, admin["user_id"])
        return jsonify({"user_id": user_id, "account_status": "ACTIVE"}), 200
    except AdminError as e:
        return jsonify({"error": str(e)}), 404


@admin_bp.route("/events", methods=["GET"])
@login_required
@role_required("ADMIN")
def events():
    return jsonify(list_all_events()), 200


@admin_bp.route("/events/<event_id>/deactivate", methods=["POST"])
@login_required
@role_required("ADMIN")
def deactivate(event_id):
    admin = request.current_user
    admin_deactivate_event(event_id, admin["user_id"])
    return jsonify({"event_id": event_id, "status": "DEACTIVATED"}), 200


@admin_bp.route("/transactions", methods=["GET"])
@login_required
@role_required("ADMIN")
def all_transactions():
    txns = list(transactions_collection().find())
    for t in txns:
        t["_id"] = str(t["_id"])
        t["event_id"] = str(t["event_id"])
        t["buyer_id"] = str(t["buyer_id"])
    return jsonify(txns), 200


@admin_bp.route("/security-logs", methods=["GET"])
@login_required
@role_required("ADMIN")
def logs():
    limit = int(request.args.get("limit", 200))
    return jsonify(security_logs(limit)), 200


@admin_bp.route("/keys", methods=["GET"])
@login_required
@role_required("ADMIN")
def keys():
    return jsonify(list_keys_for_admin(request.args.get("purpose"))), 200


@admin_bp.route("/keys/rotate", methods=["POST"])
@login_required
@role_required("ADMIN")
def rotate():
    data = request.get_json(silent=True) or {}
    purpose = data.get("purpose")
    if not purpose:
        return jsonify({"error": "purpose is required"}), 400
    new_key = rotate_key(purpose)
    return jsonify({
        "purpose": purpose,
        "new_version": new_key["key_version"],
        "status": "ACTIVE",
    }), 200


@admin_bp.route("/keys/<key_id>/revoke", methods=["POST"])
@login_required
@role_required("ADMIN")
def revoke(key_id):
    try:
        revoke_key(key_id)
        return jsonify({"key_id": key_id, "status": "REVOKED"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400