"""
auth/sessions.py — Secure session management.

Section 9 of the requirements: sessions only established after
password + OTP, tokens protected against unauthorized use, expire
after inactivity, and can be securely invalidated (logout).
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from extensions import get_db

# Session lifetime, in minutes. Set to 1 so a session expires after
# just 1 minute of inactivity (sliding expiration — any authenticated
# request resets the clock). Change this value if you need a longer
# lifetime later (e.g. for normal day-to-day development).
SESSION_VALID_MINUTES = int(os.environ.get("SESSION_VALID_MINUTES", 1))


def sessions_collection():
    return get_db()["sessions"]


def create_session(user_id, role: str) -> str:
    """
    Create a new session token after successful password + OTP
    verification. Returns the token to give to the client.
    """
    token = secrets.token_urlsafe(48)  # long, unguessable, URL-safe
    now = datetime.now(timezone.utc)

    sessions_collection().insert_one({
        "token": token,
        "user_id": user_id,
        "role": role,
        "created_at": now,
        "last_active": now,
        "expires_at": now + timedelta(minutes=SESSION_VALID_MINUTES),
    })

    return token


def get_session(token: str):
    """
    Look up a session by token. Returns None if it doesn't exist or
    has expired (and cleans up expired sessions as it goes).
    """
    session = sessions_collection().find_one({"token": token})
    if not session:
        return None

    now = datetime.now(timezone.utc)
    expires_at = session["expires_at"].replace(tzinfo=timezone.utc)

    if now > expires_at:
        sessions_collection().delete_one({"token": token})
        return None

    # sliding expiration: extend the session on activity, capped by
    # the max session lifetime rule you may want to add later
    sessions_collection().update_one(
        {"token": token},
        {"$set": {
            "last_active": now,
            "expires_at": now + timedelta(minutes=SESSION_VALID_MINUTES),
        }},
    )

    return session


def invalidate_session(token: str):
    """Logout — deletes the session so the token can never be reused."""
    sessions_collection().delete_one({"token": token})