"""
events/models.py — Event document shape + basic data-access helpers.
"""

from datetime import datetime, timezone
from bson import ObjectId
from extensions import get_db


def events_collection():
    return get_db()["events"]


def build_event_document(
    seller_id,
    name: str,
    category: str,
    date_time,
    venue: str,
    description: str,
    ticket_price: float,
    total_seats: int,
    ecc_signature: dict = None,
) -> dict:
    """
    Shape of an event document.

    ecc_signature: the seller's ECC signature over the event's critical
    fields (name, date, venue, price), so tampering can be detected —
    this is the "meaningful cryptographic role" for ECC described in
    the requirements (Section 6.2), separate from Person 1's RSA which
    handles personal-data encryption.
    """
    return {
        "seller_id": seller_id,
        "name": name,
        "category": category,
        "date_time": date_time,
        "venue": venue,
        "description": description,
        "ticket_price": ticket_price,
        "total_seats": total_seats,
        "ecc_signature": ecc_signature,  # {"r": "0x..", "s": "0x.."}
        "status": "ACTIVE",  # ACTIVE | DEACTIVATED
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


def insert_event(event_doc: dict):
    result = events_collection().insert_one(event_doc)
    return result.inserted_id


def find_event_by_id(event_id):
    oid = event_id if isinstance(event_id, ObjectId) else ObjectId(event_id)
    return events_collection().find_one({"_id": oid})


def find_events_by_seller(seller_id):
    return list(events_collection().find({"seller_id": seller_id}))


def find_active_events(filters: dict = None):
    """
    Public event listing — only ACTIVE events, from approved sellers.
    `filters` can include name/category/date/venue/price search terms.
    """
    query = {"status": "ACTIVE"}
    if filters:
        query.update(filters)
    return list(events_collection().find(query))


def update_event(event_id, updates: dict):
    oid = event_id if isinstance(event_id, ObjectId) else ObjectId(event_id)
    updates["updated_at"] = datetime.now(timezone.utc)
    events_collection().update_one({"_id": oid}, {"$set": updates})


def deactivate_event(event_id):
    update_event(event_id, {"status": "DEACTIVATED"})