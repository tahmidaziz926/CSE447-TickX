"""
admin/services.py — Admin operations: user management, seller
approval, event moderation, and security log access.
"""

from bson import ObjectId

from auth.models import users_collection
from events.models import events_collection, deactivate_event
from security_logs import log_security_event, get_recent_logs


class AdminError(Exception):
    pass


# Fields NEVER returned to any admin API response — secrets stay secret
# even from admins, per the requirements' key-protection principle.
_EXCLUDED_FIELDS = {
    "password_hash": 0,
    "password_salt": 0,
    "rsa_private_key": 0,
    "ecc_private_key": 0,
}


def list_users(role: str = None) -> list:
    """
    Return users, optionally filtered by role.
    Sensitive cryptographic and password fields are excluded.
    """

    query = {"role": role} if role else {}

    users = list(
        users_collection().find(
            query,
            _EXCLUDED_FIELDS,
        )
    )

    for user in users:
        user["_id"] = str(user["_id"])

    return users


def list_pending_sellers() -> list:
    """
    Return all sellers whose approval status is PENDING.
    """

    sellers = list(
        users_collection().find(
            {
                "role": "SELLER",
                "seller_status": "PENDING",
            },
            _EXCLUDED_FIELDS,
        )
    )

    for seller in sellers:
        seller["_id"] = str(seller["_id"])

    return sellers


def approve_seller(seller_id, admin_id) -> None:
    """
    Approve a pending seller.
    """

    oid = (
        ObjectId(seller_id)
        if isinstance(seller_id, str)
        else seller_id
    )

    result = users_collection().update_one(
        {
            "_id": oid,
            "role": "SELLER",
        },
        {
            "$set": {
                "seller_status": "APPROVED",
            }
        },
    )

    if result.matched_count == 0:
        raise AdminError("seller not found")

    log_security_event(
        "SELLER_APPROVED",
        f"Seller {seller_id} approved",
        {
            "admin_id": str(admin_id),
        },
    )


def reject_seller(seller_id, admin_id) -> None:
    """
    Reject a seller.
    """

    oid = (
        ObjectId(seller_id)
        if isinstance(seller_id, str)
        else seller_id
    )

    result = users_collection().update_one(
        {
            "_id": oid,
            "role": "SELLER",
        },
        {
            "$set": {
                "seller_status": "REJECTED",
            }
        },
    )

    if result.matched_count == 0:
        raise AdminError("seller not found")

    log_security_event(
        "SELLER_REJECTED",
        f"Seller {seller_id} rejected",
        {
            "admin_id": str(admin_id),
        },
    )


def suspend_account(user_id, admin_id) -> None:
    """
    Suspend a user account.
    """

    oid = (
        ObjectId(user_id)
        if isinstance(user_id, str)
        else user_id
    )

    result = users_collection().update_one(
        {
            "_id": oid,
        },
        {
            "$set": {
                "account_status": "SUSPENDED",
            }
        },
    )

    if result.matched_count == 0:
        raise AdminError("user not found")

    log_security_event(
        "ACCOUNT_SUSPENDED",
        f"User {user_id} suspended",
        {
            "admin_id": str(admin_id),
        },
    )


def reactivate_account(user_id, admin_id) -> None:
    """
    Reactivate a suspended user account.
    """

    oid = (
        ObjectId(user_id)
        if isinstance(user_id, str)
        else user_id
    )

    result = users_collection().update_one(
        {
            "_id": oid,
        },
        {
            "$set": {
                "account_status": "ACTIVE",
            }
        },
    )

    if result.matched_count == 0:
        raise AdminError("user not found")

    log_security_event(
        "ACCOUNT_REACTIVATED",
        f"User {user_id} reactivated",
        {
            "admin_id": str(admin_id),
        },
    )


def list_all_events() -> list:
    """
    Return all events for the admin dashboard.
    """

    events = list(
        events_collection().find()
    )

    for event in events:
        event["_id"] = str(event["_id"])

        if "seller_id" in event:
            event["seller_id"] = str(
                event["seller_id"]
            )

    return events


def admin_deactivate_event(event_id, admin_id) -> None:
    """
    Deactivate an event as an administrator.
    """

    deactivate_event(event_id)

    log_security_event(
        "EVENT_DEACTIVATED_BY_ADMIN",
        f"Event {event_id} deactivated",
        {
            "admin_id": str(admin_id),
        },
    )


def security_logs(limit: int = 200) -> list:
    """
    Return recent security logs.
    """

    return get_recent_logs(limit)