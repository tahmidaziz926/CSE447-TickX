"""
demo_tampering.py — Live demo script for the manifesto's Section 8,
Step 8: "Modify a stored ticket/transaction -> MAC verification
failure -> security log."

Run this AGAINST YOUR REAL DEV DATABASE (not the test suite's in-memory
mock) right before your presentation, or live during it:

    cd backend
    python demo_tampering.py

What it does, step by step:
  1. Creates a throwaway event + buys a ticket through the real
     purchase flow (so the MAC is generated exactly like production).
  2. Shows the ticket verifies successfully right after purchase.
  3. Directly edits the stored ticket's price field in MongoDB —
     simulating an attacker (or database-level tampering) bypassing
     the application entirely.
  4. Re-verifies the ticket and shows the MAC check now fails.
  5. Prints the resulting security_logs entry that unprotect() wrote
     automatically.
  6. Cleans up the demo data it created.

This uses your real .env / MONGODB_URI, so make sure your backend
environment is already set up (same as running `python app.py`).
"""

from bson import ObjectId
from extensions import init_db
from events.models import build_event_document, insert_event, events_collection
from events.seats import select_seat
from tickets.services import purchase_ticket, get_verified_ticket, TicketError
from tickets.models import tickets_collection, transactions_collection
from security_logs import get_recent_logs


def line(label=""):
    print("\n" + "=" * 70)
    if label:
        print(label)
        print("=" * 70)


def main():
    db = init_db()

    demo_buyer_id = ObjectId()
    demo_seller_id = ObjectId()

    line("STEP 1 — Create a throwaway event and buy a ticket normally")
    event_doc = build_event_document(
        seller_id=demo_seller_id,
        name="[DEMO] Tampering Demo Concert",
        category="Music",
        date_time="2026-12-31T20:00:00Z",
        venue="Demo Arena",
        description="Temporary event for the MAC tampering demo.",
        ticket_price=500,
        total_seats=10,
    )
    event_id = insert_event(event_doc)
    select_seat(event_id, 1, demo_buyer_id)
    result = purchase_ticket(demo_buyer_id, event_id, 1)
    ticket_id = result["ticket_id"]
    print(f"Bought ticket {ticket_id} for seat 1 at price 500.")

    line("STEP 2 — Verify the ticket right after purchase (should PASS)")
    ticket = get_verified_ticket(ticket_id, demo_buyer_id)
    print(f"Verification PASSED. Stored price: {ticket['protected_fields']['price']}")
    print(f"MAC on record: {ticket['mac'][:16]}...  key_version: {ticket['key_version']}")

    line("STEP 3 — Attacker directly edits the database (no app code involved)")
    print("Changing protected_fields.price from 500 to 1 directly in MongoDB...")
    tickets_collection().update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {"protected_fields.price": 1}},
    )
    print("Done. The MAC stored alongside the record was NOT updated —")
    print("it still reflects the original price of 500.")

    line("STEP 4 — Re-verify the tampered ticket (should FAIL)")
    try:
        get_verified_ticket(ticket_id, demo_buyer_id)
        print("UNEXPECTED: verification passed. This should not happen!")
    except TicketError as e:
        print(f"Verification FAILED as expected: {e}")

    line("STEP 5 — Security log entry written automatically by unprotect()")
    logs = get_recent_logs(limit=5)
    mac_failure_logs = [l for l in logs if l["event_type"] == "MAC_VERIFICATION_FAILED"]
    if mac_failure_logs:
        print("Most recent MAC_VERIFICATION_FAILED log entry:")
        entry = mac_failure_logs[0]
        print(f"  event_type: {entry['event_type']}")
        print(f"  message:    {entry['message']}")
        print(f"  context:    {entry['context']}")
        print(f"  timestamp:  {entry['timestamp']}")
    else:
        print("No MAC_VERIFICATION_FAILED log found — check integrity/service.py wiring.")

    line("STEP 6 — Cleanup (removing demo event/ticket/transaction)")
    cleanup(event_id, ticket_id, result["transaction_id"])
    print("Demo data removed. Done.")


def cleanup(event_id, ticket_id, transaction_id):
    events_collection().delete_one({"_id": ObjectId(event_id)})
    tickets_collection().delete_one({"_id": ObjectId(ticket_id)})
    transactions_collection().delete_one({"_id": ObjectId(transaction_id)})


if __name__ == "__main__":
    main()