"""
security_logs.py — Section 5.6: security event logging.

Shared utility — any module can call log_security_event() to record
authentication attempts, MAC failures, key lifecycle actions, seller
approvals, event modifications, ticket purchases, or admin actions.

Logs are only ever inserted, never updated or deleted through the
application, and are only readable via the admin dashboard
(admin/routes.py enforces ADMIN role) — this is what "protected
against unauthorized modification" means in practice here.
"""

from datetime import datetime, timezone
from extensions import get_db


def logs_collection():
    return get_db()["security_logs"]


def log_security_event(event_type: str, message: str, context: dict = None):
    logs_collection().insert_one({
        "event_type": event_type,
        "message": message,
        "context": context or {},
        "timestamp": datetime.now(timezone.utc),
    })


def get_recent_logs(limit: int = 200) -> list:
    logs = list(logs_collection().find().sort("timestamp", -1).limit(limit))
    for l in logs:
        l["_id"] = str(l["_id"])
        l["timestamp"] = l["timestamp"].isoformat()
    return logs