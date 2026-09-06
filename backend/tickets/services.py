"""
tickets/services.py — Ticket purchase, verification, and seller sales view.

No Flask/HTTP awareness here — routes.py calls these and translates
results into HTTP responses.
"""

from events.seats import is_seat_available, confirm_seat_sold, release_seat
from events.models import find_event_by_id
from integrity.service import protect, unprotect
from tickets.models import (
    build_transaction_document, insert_transaction, update_transaction_status,
    build_ticket_document, insert_ticket, find_ticket, find_tickets_by_buyer,
    find_transactions_by_buyer, find_transactions_by_event, find_tickets_by_event,
)


class TicketError(Exception):
    pass


def purchase_ticket(buyer_id, event_id, seat_number: int) -> dict:
    """
    Sections 2.5 / 4.1-4.5: full purchase flow.
      1. Re-verify seat availability server-side (never trust the
         frontend's idea of seat state — Tahmid's seats.py is the
         single source of truth)
      2. Create a PENDING transaction
      3. Simulate payment (always succeeds — Section 4.3, no real
         financial transactions for this academic project)
      4. On success: confirm seat SOLD, generate a MAC-protected
         ticket, mark transaction SUCCESSFUL
      5. On failure: mark transaction FAILED, release the seat hold
    """
    event = find_event_by_id(event_id)
    if event is None:
        raise TicketError("event not found")

    amount = event["ticket_price"]
    transaction_doc = build_transaction_document(buyer_id, event_id, seat_number, amount)
    transaction_id = insert_transaction(transaction_doc)

    # --- Simulated payment (Section 4.3) ---
    payment_successful = True  # always succeeds in this academic simulation

    if not payment_successful:
        update_transaction_status(transaction_id, "FAILED")
        release_seat(event_id, seat_number, buyer_id)
        raise TicketError("payment failed")

    # This is the actual authority check: confirm_seat_sold() only
    # succeeds if the seat is currently SELECTED (held) by THIS buyer —
    # protects against a race where the hold expired or was never
    # actually made by this buyer.
    sold = confirm_seat_sold(event_id, seat_number, buyer_id)
    if not sold:
        update_transaction_status(transaction_id, "FAILED")
        raise TicketError("seat was no longer available at time of payment")

    update_transaction_status(transaction_id, "SUCCESSFUL")

    protected_fields = {
        "event_id": str(event_id),
        "seat_number": seat_number,
        "buyer_id": str(buyer_id),
        "price": amount,
        "transaction_id": str(transaction_id),
    }
    mac_info = protect("ticket-mac", protected_fields)

    ticket_doc = build_ticket_document(
        buyer_id, event_id, seat_number, transaction_id, protected_fields, mac_info
    )
    ticket_id = insert_ticket(ticket_doc)

    return {
        "ticket_id": str(ticket_id),
        "transaction_id": str(transaction_id),
        "status": "SUCCESSFUL",
    }


def get_verified_ticket(ticket_id, requesting_user_id) -> dict:
    """
    Section 2.6: buyers can only access their own tickets. Verifies
    the ticket's MAC before returning it — Section 4.2: "Invalid or
    tampered ticket records will be rejected by the system."
    """
    ticket = find_ticket(ticket_id)
    if ticket is None:
        raise TicketError("ticket not found")

    if str(ticket["buyer_id"]) != str(requesting_user_id):
        raise TicketError("you do not have permission to view this ticket")

    valid = unprotect(
        "ticket-mac", ticket["protected_fields"], ticket["mac"], ticket["key_version"],
        context={"ticket_id": str(ticket["_id"])},
    )
    if not valid:
        raise TicketError("ticket integrity check failed — this record may have been tampered with")

    ticket["_id"] = str(ticket["_id"])
    ticket["event_id"] = str(ticket["event_id"])
    ticket["buyer_id"] = str(ticket["buyer_id"])
    ticket["transaction_id"] = str(ticket["transaction_id"])
    return ticket


def list_my_tickets(buyer_id) -> list:
    tickets = find_tickets_by_buyer(buyer_id)
    verified = []
    for t in tickets:
        try:
            verified.append(get_verified_ticket(t["_id"], buyer_id))
        except TicketError:
            # A tampered ticket is silently excluded from the buyer's
            # list rather than crashing the whole request; the failed
            # verification is still recorded in security_logs by
            # unprotect() itself.
            continue
    return verified


def list_my_transactions(buyer_id) -> list:
    transactions = find_transactions_by_buyer(buyer_id)
    for t in transactions:
        t["_id"] = str(t["_id"])
        t["event_id"] = str(t["event_id"])
        t["buyer_id"] = str(t["buyer_id"])
    return transactions


def get_seller_sales(event_id, seller_id) -> dict:
    """Section 3.5: seller sales dashboard for one of their events."""
    event = find_event_by_id(event_id)
    if event is None:
        raise TicketError("event not found")
    if str(event["seller_id"]) != str(seller_id):
        raise TicketError("you do not have permission to view this event's sales")

    tickets = find_tickets_by_event(event_id)
    transactions = find_transactions_by_event(event_id)

    sold_count = len(tickets)
    remaining = event["total_seats"] - sold_count

    for t in transactions:
        t["_id"] = str(t["_id"])
        t["event_id"] = str(t["event_id"])
        t["buyer_id"] = str(t["buyer_id"])

    return {
        "event_id": str(event_id),
        "total_seats": event["total_seats"],
        "sold": sold_count,
        "remaining": remaining,
        "transactions": transactions,
    }