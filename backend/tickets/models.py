"""
tickets/models.py — Ticket + Transaction document shapes + DB access.
"""

from datetime import datetime, timezone
from bson import ObjectId
from extensions import get_db


def tickets_collection():
    return get_db()["tickets"]


def transactions_collection():
    return get_db()["transactions"]


def build_transaction_document(buyer_id, event_id, seat_number: int, amount: float) -> dict:
    return {
        "buyer_id": buyer_id,
        "event_id": event_id,
        "seat_number": seat_number,
        "amount": amount,
        "status": "PENDING",  # PENDING | SUCCESSFUL | FAILED | CANCELLED
        "created_at": datetime.now(timezone.utc),
    }


def insert_transaction(doc: dict):
    return transactions_collection().insert_one(doc).inserted_id


def update_transaction_status(transaction_id, status: str):
    oid = transaction_id if isinstance(transaction_id, ObjectId) else ObjectId(transaction_id)
    transactions_collection().update_one({"_id": oid}, {"$set": {"status": status}})


def find_transaction(transaction_id):
    oid = transaction_id if isinstance(transaction_id, ObjectId) else ObjectId(transaction_id)
    return transactions_collection().find_one({"_id": oid})


def find_transactions_by_buyer(buyer_id):
    return list(transactions_collection().find({"buyer_id": buyer_id}))


def find_transactions_by_event(event_id):
    return list(transactions_collection().find({"event_id": event_id}))


def build_ticket_document(buyer_id, event_id, seat_number: int, transaction_id, protected_fields: dict, mac_info: dict) -> dict:
    """
    protected_fields is the canonical dict that was MAC'd (event, seat,
    buyer, price, transaction info) — stored alongside the MAC/version
    so it can be re-verified later. This is integrity protection, not
    confidentiality — RSA (Person 1) handles encrypting personal data;
    MAC here just detects tampering.
    """
    return {
        "ticket_id": None,  # set to the Mongo _id string after insert
        "buyer_id": buyer_id,
        "event_id": event_id,
        "seat_number": seat_number,
        "transaction_id": transaction_id,
        "protected_fields": protected_fields,
        "mac": mac_info["mac"],
        "key_version": mac_info["key_version"],
        "created_at": datetime.now(timezone.utc),
    }


def insert_ticket(doc: dict):
    ticket_id = tickets_collection().insert_one(doc).inserted_id
    tickets_collection().update_one({"_id": ticket_id}, {"$set": {"ticket_id": str(ticket_id)}})
    return ticket_id


def find_ticket(ticket_id):
    oid = ticket_id if isinstance(ticket_id, ObjectId) else ObjectId(ticket_id)
    return tickets_collection().find_one({"_id": oid})


def find_tickets_by_buyer(buyer_id):
    return list(tickets_collection().find({"buyer_id": buyer_id}))


def find_tickets_by_event(event_id):
    return list(tickets_collection().find({"event_id": event_id}))