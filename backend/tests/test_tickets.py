"""
tests/test_tickets.py — tickets/services.py purchase flow + integrity
(MAC) tampering detection tests.

This is the automated version of the manifesto's "final tampering
demonstration": buy a ticket, modify a stored field directly in the
DB, then confirm the system detects it and refuses to trust the
record.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId
from events.models import build_event_document, insert_event
from events.seats import select_seat
from tickets.services import (
    purchase_ticket, get_verified_ticket, list_my_transactions,
    get_seller_sales, TicketError,
)
from tickets.models import tickets_collection, transactions_collection


BUYER_ID = ObjectId()
SELLER_ID = ObjectId()


def _make_event(mock_db, total_seats=10, price=500):
    event_doc = build_event_document(
        seller_id=SELLER_ID, name="Test Concert", category="Music",
        date_time="2026-12-01T20:00:00Z", venue="Test Arena",
        description="A test event", ticket_price=price, total_seats=total_seats,
    )
    return insert_event(event_doc)


def test_purchase_ticket_succeeds_for_selected_seat(mock_db):
    event_id = _make_event(mock_db)
    select_seat(event_id, 5, BUYER_ID)

    result = purchase_ticket(BUYER_ID, event_id, 5)

    assert result["status"] == "SUCCESSFUL"
    assert "ticket_id" in result
    assert "transaction_id" in result


def test_purchase_ticket_fails_if_seat_was_never_selected(mock_db):
    """
    The backend re-checks that THIS buyer actually holds the seat
    before confirming the sale — never trusts the frontend's claim.
    """
    event_id = _make_event(mock_db)
    # note: no select_seat() call — buyer never actually reserved seat 5

    try:
        purchase_ticket(BUYER_ID, event_id, 5)
        assert False, "expected purchase to fail without a prior seat selection"
    except TicketError:
        pass

    # the transaction should be recorded as FAILED, not silently dropped
    txns = list_my_transactions(BUYER_ID)
    assert len(txns) == 1
    assert txns[0]["status"] == "FAILED"


def test_purchase_ticket_fails_for_nonexistent_event(mock_db):
    fake_event_id = ObjectId()
    try:
        purchase_ticket(BUYER_ID, fake_event_id, 1)
        assert False, "expected TicketError for a nonexistent event"
    except TicketError:
        pass


def test_get_verified_ticket_succeeds_for_untampered_ticket(mock_db):
    event_id = _make_event(mock_db)
    select_seat(event_id, 3, BUYER_ID)
    result = purchase_ticket(BUYER_ID, event_id, 3)

    ticket = get_verified_ticket(result["ticket_id"], BUYER_ID)
    assert ticket["seat_number"] == 3
    assert ticket["mac"]  # MAC is present


def test_tampered_ticket_fails_mac_verification(mock_db):
    """
    The core tampering demo: buy a ticket, directly modify a protected
    field in MongoDB (simulating an attacker or DB-level tampering),
    then confirm verification rejects it.
    """
    event_id = _make_event(mock_db, price=500)
    select_seat(event_id, 7, BUYER_ID)
    result = purchase_ticket(BUYER_ID, event_id, 7)

    # Directly tamper with the stored ticket's protected price field,
    # bypassing the application layer entirely — as if someone edited
    # the database directly.
    tickets_collection().update_one(
        {"_id": ObjectId(result["ticket_id"])},
        {"$set": {"protected_fields.price": 1}},  # attacker tries to "buy" a $500 seat for $1
    )

    try:
        get_verified_ticket(result["ticket_id"], BUYER_ID)
        assert False, "expected tampered ticket to fail MAC verification"
    except TicketError as e:
        assert "tampered" in str(e).lower() or "integrity" in str(e).lower()


def test_tampered_ticket_writes_a_security_log_entry(mock_db):
    event_id = _make_event(mock_db)
    select_seat(event_id, 2, BUYER_ID)
    result = purchase_ticket(BUYER_ID, event_id, 2)

    tickets_collection().update_one(
        {"_id": ObjectId(result["ticket_id"])},
        {"$set": {"protected_fields.seat_number": 999}},
    )

    try:
        get_verified_ticket(result["ticket_id"], BUYER_ID)
    except TicketError:
        pass

    logs = list(mock_db["security_logs"].find({"event_type": "MAC_VERIFICATION_FAILED"}))
    assert len(logs) >= 1


def test_tampered_ticket_is_excluded_from_list_my_tickets(mock_db):
    """
    list_my_tickets() silently excludes tampered records rather than
    crashing the whole request (the failure is still logged, via the
    test above).
    """
    from tickets.services import list_my_tickets

    event_id = _make_event(mock_db)
    select_seat(event_id, 9, BUYER_ID)
    result = purchase_ticket(BUYER_ID, event_id, 9)

    tickets_collection().update_one(
        {"_id": ObjectId(result["ticket_id"])},
        {"$set": {"protected_fields.buyer_id": "someone-else"}},
    )

    tickets = list_my_tickets(BUYER_ID)
    assert all(t["ticket_id"] != result["ticket_id"] for t in tickets) or len(tickets) == 0


def test_buyer_cannot_view_another_buyers_ticket(mock_db):
    other_buyer = ObjectId()
    event_id = _make_event(mock_db)
    select_seat(event_id, 1, BUYER_ID)
    result = purchase_ticket(BUYER_ID, event_id, 1)

    try:
        get_verified_ticket(result["ticket_id"], other_buyer)
        assert False, "expected a permission error for viewing someone else's ticket"
    except TicketError:
        pass


def test_seller_sales_view_reports_correct_counts(mock_db):
    event_id = _make_event(mock_db, total_seats=5)
    select_seat(event_id, 1, BUYER_ID)
    purchase_ticket(BUYER_ID, event_id, 1)

    sales = get_seller_sales(event_id, SELLER_ID)
    assert sales["sold"] == 1
    assert sales["remaining"] == 4


def test_seller_cannot_view_another_sellers_sales(mock_db):
    other_seller = ObjectId()
    event_id = _make_event(mock_db)

    try:
        get_seller_sales(event_id, other_seller)
        assert False, "expected a permission error"
    except TicketError:
        pass