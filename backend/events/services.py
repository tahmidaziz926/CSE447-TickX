"""
events/services.py — Business logic for event management.

No Flask/HTTP awareness here — routes.py calls these functions and
translates results into HTTP responses.
"""

from crypto import ecc
from events.models import (
    build_event_document, insert_event, find_event_by_id,
    find_events_by_seller, find_active_events, update_event, deactivate_event,
)
from events.seats import generate_seat_grid


class EventError(Exception):
    """Raised for expected event-management failures (bad input,
    ownership violations, etc.) — routes.py catches this for clean
    4xx responses."""
    pass


def _canonical_event_string(name, category, date_time, venue, ticket_price) -> bytes:
    """
    Deterministic representation of an event's critical fields, so the
    same event always produces the same string to sign/verify against
    — matches the "deterministic canonicalization" principle Pallab's
    MAC module also relies on for its own protected records.
    """
    return f"{name}|{category}|{date_time}|{venue}|{ticket_price}".encode("utf-8")


def create_event(
    seller_id,
    seller_role: str,
    seller_status: str,
    seller_ecc_private_key: int,
    name: str,
    category: str,
    date_time,
    venue: str,
    description: str,
    ticket_price: float,
    total_seats: int,
) -> dict:
    """
    Create a new event. Only approved sellers can publish.
    Signs the event's critical fields with the seller's ECC private
    key, so any later tampering with those fields can be detected.
    """
    if seller_role != "SELLER":
        raise EventError("only sellers can create events")

    if seller_status != "APPROVED":
        raise EventError("your seller account is pending admin approval")

    if not name or not venue:
        raise EventError("event name and venue are required")

    if ticket_price < 0:
        raise EventError("ticket price cannot be negative")

    generate_seat_grid(None, total_seats)  # validates total_seats > 0

    message = _canonical_event_string(name, category, date_time, venue, ticket_price)
    signature = ecc.sign(message, seller_ecc_private_key)

    event_doc = build_event_document(
        seller_id=seller_id,
        name=name,
        category=category,
        date_time=date_time,
        venue=venue,
        description=description,
        ticket_price=ticket_price,
        total_seats=total_seats,
        ecc_signature=ecc.signature_to_dict(signature),
    )
    event_id = insert_event(event_doc)

    return {"event_id": str(event_id), "status": "ACTIVE"}


def verify_event_integrity(event_doc: dict, seller_ecc_public_key) -> bool:
    """
    Verify an event's ECC signature still matches its current fields —
    call this before trusting/displaying an event, to detect
    unauthorized modification (the same principle as Pallab's MAC
    verification, using ECC signatures instead of HMAC).
    """
    if not event_doc.get("ecc_signature"):
        return False

    message = _canonical_event_string(
        event_doc["name"], event_doc["category"],
        event_doc["date_time"], event_doc["venue"], event_doc["ticket_price"],
    )
    signature = ecc.signature_from_dict(event_doc["ecc_signature"])
    return ecc.verify(message, signature, seller_ecc_public_key)


def list_public_events(filters: dict = None) -> list:
    """Buyer-facing event browsing — active events only."""
    events = find_active_events(filters)
    for e in events:
        e["_id"] = str(e["_id"])
        e["seller_id"] = str(e["seller_id"])
    return events


def get_event_details(event_id) -> dict:
    event = find_event_by_id(event_id)
    if event is None:
        raise EventError("event not found")
    event["_id"] = str(event["_id"])
    event["seller_id"] = str(event["seller_id"])
    return event


def list_seller_events(seller_id) -> list:
    events = find_events_by_seller(seller_id)
    for e in events:
        e["_id"] = str(e["_id"])
        e["seller_id"] = str(e["seller_id"])
    return events


def _assert_owns_event(event_id, seller_id):
    """Sellers can only modify events associated with their own accounts."""
    event = find_event_by_id(event_id)
    if event is None:
        raise EventError("event not found")
    if str(event["seller_id"]) != str(seller_id):
        raise EventError("you do not have permission to modify this event")
    return event


def update_seller_event(event_id, seller_id, seller_ecc_private_key, updates: dict):
    """
    Update an event's own fields. Re-signs the event if any of the
    critical (signed) fields changed, so the signature always matches
    the current content.
    """
    event = _assert_owns_event(event_id, seller_id)

    merged = {**event, **updates}
    critical_changed = any(
        updates.get(f) is not None and updates[f] != event.get(f)
        for f in ("name", "category", "date_time", "venue", "ticket_price")
    )

    if critical_changed:
        message = _canonical_event_string(
            merged["name"], merged["category"],
            merged["date_time"], merged["venue"], merged["ticket_price"],
        )
        signature = ecc.sign(message, seller_ecc_private_key)
        updates["ecc_signature"] = ecc.signature_to_dict(signature)

    update_event(event_id, updates)
    return {"event_id": str(event_id), "updated": True}


def delete_seller_event(event_id, seller_id):
    _assert_owns_event(event_id, seller_id)
    deactivate_event(event_id)
    return {"event_id": str(event_id), "status": "DEACTIVATED"}