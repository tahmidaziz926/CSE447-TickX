"""
admin/routes.py — HTTP layer for the admin dashboard.

Every route requires ADMIN role.
"""

from flask import Blueprint, request, jsonify

from auth.middleware import login_required, role_required

from admin.services import (
    list_users,
    list_pending_sellers,
    approve_seller,
    reject_seller,
    suspend_account,
    reactivate_account,
    list_all_events,
    admin_deactivate_event,
    security_logs,
    AdminError,
)

from keys.service import (
    list_keys_for_admin,
    rotate_key,
    revoke_key,
)

from tickets.models import transactions_collection


admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------

@admin_bp.route("/users", methods=["GET"])
@login_required
@role_required("ADMIN")
def users():
    role = request.args.get("role")

    return jsonify(
        list_users(role)
    ), 200


# ---------------------------------------------------------------------------
# SELLER MANAGEMENT
# ---------------------------------------------------------------------------

@admin_bp.route("/sellers/pending", methods=["GET"])
@login_required
@role_required("ADMIN")
def pending_sellers():
    """
    Return all pending seller approval requests.
    """

    sellers = list_pending_sellers()

    return jsonify(sellers), 200


@admin_bp.route("/sellers/<seller_id>/approve", methods=["POST"])
@login_required
@role_required("ADMIN")
def approve(seller_id):
    """
    Approve a seller.
    """

    admin = request.current_user

    try:
        approve_seller(
            seller_id,
            admin["user_id"],
        )

        return jsonify({
            "seller_id": seller_id,
            "seller_status": "APPROVED",
        }), 200

    except AdminError as error:
        return jsonify({
            "error": str(error),
        }), 404


@admin_bp.route("/sellers/<seller_id>/reject", methods=["POST"])
@login_required
@role_required("ADMIN")
def reject(seller_id):
    """
    Reject a seller.
    """

    admin = request.current_user

    try:
        reject_seller(
            seller_id,
            admin["user_id"],
        )

        return jsonify({
            "seller_id": seller_id,
            "seller_status": "REJECTED",
        }), 200

    except AdminError as error:
        return jsonify({
            "error": str(error),
        }), 404


# ---------------------------------------------------------------------------
# ACCOUNT MANAGEMENT
# ---------------------------------------------------------------------------

@admin_bp.route("/users/<user_id>/suspend", methods=["POST"])
@login_required
@role_required("ADMIN")
def suspend(user_id):
    """
    Suspend a user account.
    """

    admin = request.current_user

    try:
        suspend_account(
            user_id,
            admin["user_id"],
        )

        return jsonify({
            "user_id": user_id,
            "account_status": "SUSPENDED",
        }), 200

    except AdminError as error:
        return jsonify({
            "error": str(error),
        }), 404


@admin_bp.route("/users/<user_id>/reactivate", methods=["POST"])
@login_required
@role_required("ADMIN")
def reactivate(user_id):
    """
    Reactivate a user account.
    """

    admin = request.current_user

    try:
        reactivate_account(
            user_id,
            admin["user_id"],
        )

        return jsonify({
            "user_id": user_id,
            "account_status": "ACTIVE",
        }), 200

    except AdminError as error:
        return jsonify({
            "error": str(error),
        }), 404


# ---------------------------------------------------------------------------
# EVENT MODERATION
# ---------------------------------------------------------------------------

@admin_bp.route("/events", methods=["GET"])
@login_required
@role_required("ADMIN")
def events():
    """
    Return all events.
    """

    return jsonify(
        list_all_events()
    ), 200


@admin_bp.route("/events/<event_id>/deactivate", methods=["POST"])
@login_required
@role_required("ADMIN")
def deactivate(event_id):
    """
    Deactivate an event.
    """

    admin = request.current_user

    try:
        admin_deactivate_event(
            event_id,
            admin["user_id"],
        )

        return jsonify({
            "event_id": event_id,
            "status": "DEACTIVATED",
        }), 200

    except Exception as error:
        return jsonify({
            "error": str(error),
        }), 400


# ---------------------------------------------------------------------------
# TRANSACTIONS
# ---------------------------------------------------------------------------

@admin_bp.route("/transactions", methods=["GET"])
@login_required
@role_required("ADMIN")
def all_transactions():
    """
    Return all transactions.
    """

    transactions = list(
        transactions_collection().find()
    )

    for transaction in transactions:

        transaction["_id"] = str(
            transaction["_id"]
        )

        if "event_id" in transaction:
            transaction["event_id"] = str(
                transaction["event_id"]
            )

        if "buyer_id" in transaction:
            transaction["buyer_id"] = str(
                transaction["buyer_id"]
            )

    return jsonify(transactions), 200


# ---------------------------------------------------------------------------
# SECURITY LOGS
# ---------------------------------------------------------------------------

@admin_bp.route("/security-logs", methods=["GET"])
@login_required
@role_required("ADMIN")
def logs():
    """
    Return recent security logs.
    """

    try:
        limit = int(
            request.args.get("limit", 200)
        )

    except ValueError:
        return jsonify({
            "error": "limit must be a valid number",
        }), 400

    return jsonify(
        security_logs(limit)
    ), 200


# ---------------------------------------------------------------------------
# KEY MANAGEMENT
# ---------------------------------------------------------------------------

@admin_bp.route("/keys", methods=["GET"])
@login_required
@role_required("ADMIN")
def keys():
    """
    Return key metadata for administrators.
    """

    purpose = request.args.get("purpose")

    return jsonify(
        list_keys_for_admin(purpose)
    ), 200


@admin_bp.route("/keys/rotate", methods=["POST"])
@login_required
@role_required("ADMIN")
def rotate():
    """
    Rotate a cryptographic key.
    """

    data = request.get_json(
        silent=True
    ) or {}

    purpose = data.get("purpose")

    if not purpose:
        return jsonify({
            "error": "purpose is required",
        }), 400

    try:
        new_key = rotate_key(purpose)

        return jsonify({
            "purpose": purpose,
            "new_version": new_key["key_version"],
            "status": "ACTIVE",
        }), 200

    except Exception as error:
        return jsonify({
            "error": str(error),
        }), 400


@admin_bp.route("/keys/<key_id>/revoke", methods=["POST"])
@login_required
@role_required("ADMIN")
def revoke(key_id):
    """
    Revoke a cryptographic key.
    """

    try:
        revoke_key(key_id)

        return jsonify({
            "key_id": key_id,
            "status": "REVOKED",
        }), 200

    except Exception as error:
        return jsonify({
            "error": str(error),
        }), 400