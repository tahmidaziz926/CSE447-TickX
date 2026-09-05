"""
events/routes.py — HTTP layer for event management.

Registers a Flask Blueprint — in app.py:
    from events.routes import events_bp
    app.register_blueprint(events_bp, url_prefix="/api/events")

Uses Person 1's auth middleware (login_required, role_required) —
this is the pattern every teammate's routes should follow, so RBAC is
enforced consistently across the whole app.

Endpoints:
    POST /api/events              -> seller creates an event
    GET  /api/events               -> buyer browses active events
    GET  /api/events/<id>            -> event details
    GET  /api/events/mine              -> seller's own events
    PUT  /api/events/<id>                -> seller updates own event
    DELETE /api/events/<id>                -> seller deactivates own event
    GET  /api/events/<id>/seats               -> seat grid status
    POST /api/events/<id>/seats/<n>/select      -> buyer selects a seat
    POST /api/events/<id>/seats/<n>/release       -> buyer releases a held seat
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required, role_required
from events.services import (
    create_event, list_public_events, get_event_details, list_seller_events,
    update_seller_event, delete_seller_event, EventError,
)
from events.seats import get_seat_statuses, select_seat, release_seat
from events.models import find_event_by_id

events_bp = Blueprint("events", __name__)


@events_bp.route("", methods=["POST"])
@login_required
@role_required("SELLER")
def create():
    user = request.current_user
    data = request.get_json(silent=True) or {}

    # NOTE: seller_status and ecc_private_key would normally come from
    # the user's DB record — this assumes auth/models.py's user
    # document has been extended with these fields once Person 1's
    # registration flow also generates/stores ECC keys (currently a
    # TODO in auth/services.py's register_user()).
    from auth.models import users_collection
    from bson import ObjectId
    seller = users_collection().find_one({"_id": ObjectId(user["user_id"])})

    try:
        result = create_event(
            seller_id=user["user_id"],
            seller_role=user["role"],
            seller_status=seller.get("seller_status"),
            seller_ecc_private_key=seller.get("ecc_private_key"),
            name=data.get("name"),
            category=data.get("category"),
            date_time=data.get("date_time"),
            venue=data.get("venue"),
            description=data.get("description", ""),
            ticket_price=float(data.get("ticket_price", 0)),
            total_seats=int(data.get("total_seats", 0)),
        )
        return jsonify(result), 201
    except EventError as e:
        return jsonify({"error": str(e)}), 400


@events_bp.route("", methods=["GET"])
def browse():
    """Public — no login required, matches Section 2.2 (buyers browse
    events published by approved sellers)."""
    filters = {}
    if request.args.get("category"):
        filters["category"] = request.args["category"]
    if request.args.get("name"):
        filters["name"] = {"$regex": request.args["name"], "$options": "i"}

    events = list_public_events(filters)
    return jsonify(events), 200


@events_bp.route("/mine", methods=["GET"])
@login_required
@role_required("SELLER")
def mine():
    user = request.current_user
    events = list_seller_events(user["user_id"])
    return jsonify(events), 200


@events_bp.route("/<event_id>", methods=["GET"])
def details(event_id):
    try:
        event = get_event_details(event_id)
        return jsonify(event), 200
    except EventError as e:
        return jsonify({"error": str(e)}), 404


@events_bp.route("/<event_id>", methods=["PUT"])
@login_required
@role_required("SELLER")
def update(event_id):
    user = request.current_user
    data = request.get_json(silent=True) or {}

    from auth.models import users_collection
    from bson import ObjectId
    seller = users_collection().find_one({"_id": ObjectId(user["user_id"])})

    try:
        result = update_seller_event(
            event_id, user["user_id"], seller.get("ecc_private_key"), data
        )
        return jsonify(result), 200
    except EventError as e:
        return jsonify({"error": str(e)}), 403


@events_bp.route("/<event_id>", methods=["DELETE"])
@login_required
@role_required("SELLER")
def delete(event_id):
    user = request.current_user
    try:
        result = delete_seller_event(event_id, user["user_id"])
        return jsonify(result), 200
    except EventError as e:
        return jsonify({"error": str(e)}), 403


@events_bp.route("/<event_id>/seats", methods=["GET"])
def seat_grid(event_id):
    event = find_event_by_id(event_id)
    if event is None:
        return jsonify({"error": "event not found"}), 404
    statuses = get_seat_statuses(event_id, event["total_seats"])
    return jsonify(statuses), 200


@events_bp.route("/<event_id>/seats/<int:seat_number>/select", methods=["POST"])
@login_required
def select(event_id, seat_number):
    user = request.current_user
    ok = select_seat(event_id, seat_number, user["user_id"])
    if not ok:
        return jsonify({"error": "seat is not available"}), 409
    return jsonify({"seat_number": seat_number, "status": "SELECTED"}), 200


@events_bp.route("/<event_id>/seats/<int:seat_number>/release", methods=["POST"])
@login_required
def release(event_id, seat_number):
    user = request.current_user
    release_seat(event_id, seat_number, user["user_id"])
    return jsonify({"seat_number": seat_number, "status": "AVAILABLE"}), 200