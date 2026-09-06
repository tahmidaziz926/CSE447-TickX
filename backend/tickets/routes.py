"""
tickets/routes.py — HTTP layer for ticket purchase, retrieval, and
transaction history.

Two blueprints defined here (both registered in app.py) because the
requirements specify distinct top-level paths:
    POST /api/tickets/purchase
    GET  /api/tickets/my
    GET  /api/transactions/my   <- separate prefix, not /api/tickets/transactions/my
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required, role_required
from tickets.services import (
    purchase_ticket, get_verified_ticket, list_my_tickets, list_my_transactions,
    get_seller_sales, TicketError,
)

tickets_bp = Blueprint("tickets", __name__)
transactions_bp = Blueprint("transactions", __name__)


@tickets_bp.route("/purchase", methods=["POST"])
@login_required
def purchase():
    user = request.current_user
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    seat_number = data.get("seat_number")

    if event_id is None or seat_number is None:
        return jsonify({"error": "event_id and seat_number are required"}), 400

    try:
        result = purchase_ticket(user["user_id"], event_id, int(seat_number))
        return jsonify(result), 201
    except TicketError as e:
        return jsonify({"error": str(e)}), 400


@tickets_bp.route("/my", methods=["GET"])
@login_required
def my_tickets():
    user = request.current_user
    tickets = list_my_tickets(user["user_id"])
    return jsonify(tickets), 200


@tickets_bp.route("/<ticket_id>", methods=["GET"])
@login_required
def ticket_details(ticket_id):
    user = request.current_user
    try:
        ticket = get_verified_ticket(ticket_id, user["user_id"])
        return jsonify(ticket), 200
    except TicketError as e:
        return jsonify({"error": str(e)}), 403


@tickets_bp.route("/sales/<event_id>", methods=["GET"])
@login_required
@role_required("SELLER")
def seller_sales(event_id):
    user = request.current_user
    try:
        sales = get_seller_sales(event_id, user["user_id"])
        return jsonify(sales), 200
    except TicketError as e:
        return jsonify({"error": str(e)}), 403


@transactions_bp.route("/my", methods=["GET"])
@login_required
def my_transactions():
    user = request.current_user
    transactions = list_my_transactions(user["user_id"])
    return jsonify(transactions), 200