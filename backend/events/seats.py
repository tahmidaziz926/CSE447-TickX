"""
events/seats.py — Seat grid generation + availability logic.

Kept separate from events/services.py because seat logic is used by
BOTH sides of the app: sellers define seat counts, buyers check
availability and reserve seats during purchase. Person 3 (Pallab)'s
ticket-purchase code also imports directly from this module
(`from events.seats import check_and_reserve_seat`) rather than going
through seller-specific event logic.

Seat states: AVAILABLE -> SELECTED (temporary hold) -> SOLD.
"AVAILABLE" is derived (absence of a seats doc = available), so we
only ever write documents for seats that are SELECTED or SOLD.
"""

from datetime import datetime, timedelta, timezone
from bson import ObjectId
from extensions import get_db

# How long a "SELECTED" (temporary hold) lasts before it's released
# back to AVAILABLE automatically, so a buyer who abandons checkout
# doesn't lock a seat forever.
SELECTION_HOLD_MINUTES = 5


def seats_collection():
    return get_db()["seats"]


def generate_seat_grid(event_id, total_seats: int):
    """
    Called once, at event creation. Doesn't pre-write documents for
    every seat (that would be wasteful for large events) — seats are
    implicitly AVAILABLE until a document exists for them.
    Just validates the count and returns the seat numbering scheme.
    """
    if total_seats < 1:
        raise ValueError("total_seats must be at least 1")
    return list(range(1, total_seats + 1))  # seat numbers 1..N


def _release_expired_holds(event_id):
    """Any SELECTED seat whose hold has expired reverts to AVAILABLE
    (i.e. its document is deleted, since AVAILABLE = no document)."""
    now = datetime.now(timezone.utc)
    seats_collection().delete_many({
        "event_id": event_id,
        "status": "SELECTED",
        "held_until": {"$lt": now},
    })


def get_seat_statuses(event_id, total_seats: int) -> dict:
    """
    Returns {seat_number: "AVAILABLE" | "SELECTED" | "SOLD"} for every
    seat in the event, for rendering the seat grid UI.
    """
    _release_expired_holds(event_id)

    statuses = {n: "AVAILABLE" for n in range(1, total_seats + 1)}
    taken = seats_collection().find({"event_id": event_id})
    for doc in taken:
        statuses[doc["seat_number"]] = doc["status"]
    return statuses


def select_seat(event_id, seat_number: int, buyer_id) -> bool:
    """
    Temporarily reserve a seat during checkout. Returns False if the
    seat is already SELECTED (by anyone) or SOLD — this is the
    "backend performs the final availability check" requirement:
    the frontend's idea of seat state is never trusted as authority.
    """
    _release_expired_holds(event_id)

    existing = seats_collection().find_one({
        "event_id": event_id,
        "seat_number": seat_number,
    })
    if existing is not None:
        return False  # already SELECTED or SOLD by someone

    held_until = datetime.now(timezone.utc) + timedelta(minutes=SELECTION_HOLD_MINUTES)
    try:
        seats_collection().insert_one({
            "event_id": event_id,
            "seat_number": seat_number,
            "status": "SELECTED",
            "buyer_id": buyer_id,
            "held_until": held_until,
        })
        return True
    except Exception:
        # a duplicate-key race (two buyers clicking the same seat at
        # the same instant) lands here if you add a unique index on
        # (event_id, seat_number) — recommended for production
        return False


def confirm_seat_sold(event_id, seat_number: int, buyer_id) -> bool:
    """
    Called after successful payment (Pallab's ticket-purchase flow).
    Only succeeds if the seat is currently SELECTED by this same
    buyer — prevents marking someone else's held/sold seat as sold
    out from under them.
    """
    result = seats_collection().update_one(
        {
            "event_id": event_id,
            "seat_number": seat_number,
            "status": "SELECTED",
            "buyer_id": buyer_id,
        },
        {"$set": {"status": "SOLD"}, "$unset": {"held_until": ""}},
    )
    return result.modified_count == 1


def release_seat(event_id, seat_number: int, buyer_id):
    """Buyer cancels/backs out of checkout before paying."""
    seats_collection().delete_one({
        "event_id": event_id,
        "seat_number": seat_number,
        "status": "SELECTED",
        "buyer_id": buyer_id,
    })


def is_seat_available(event_id, seat_number: int) -> bool:
    _release_expired_holds(event_id)
    existing = seats_collection().find_one({
        "event_id": event_id,
        "seat_number": seat_number,
    })
    return existing is None