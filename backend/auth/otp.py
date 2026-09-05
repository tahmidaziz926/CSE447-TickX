"""
auth/otp.py — OTP (One-Time Password) generation & verification.

Section 1.3 of the requirements: "After successful password
verification, users must complete Two-Factor Authentication (OTP
verification)." This module implements that second factor.

For this academic project, OTPs are printed to the Flask console
instead of actually being sent via SMS/email (no real SMS/email
provider is required by the spec).
"""

import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from extensions import get_db


OTP_LENGTH = 6
OTP_VALID_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


def otp_collection():
    return get_db()["otp_challenges"]


def generate_otp(user_id) -> str:
    """
    Generate a new numeric OTP for a user, store it with an expiry,
    and return the OTP.

    Any previous unexpired OTP for this user is invalidated.
    """

    # Always store user_id as ObjectId when possible.
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:
            pass

    code = "".join(
        secrets.choice("0123456789")
        for _ in range(OTP_LENGTH)
    )

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=OTP_VALID_MINUTES)
    )

    otp_collection().update_one(
        {"user_id": user_id},
        {
            "$set": {
                "code": code,
                "expires_at": expires_at,
                "verified": False,
                "attempts": 0,
            }
        },
        upsert=True,
    )

    print(
        f"[OTP] Code for user {user_id}: "
        f"{code} (valid {OTP_VALID_MINUTES} min)"
    )

    return code


def verify_otp(user_id, submitted_code: str) -> bool:
    """
    Verify a submitted OTP against the stored challenge.

    Rejects:
    - nonexistent OTPs
    - expired OTPs
    - incorrect codes
    - codes after too many failed attempts
    """

    # The frontend sends the user ID as a string.
    # Convert it back to MongoDB ObjectId before querying.
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:
            return False

    record = otp_collection().find_one(
        {"user_id": user_id}
    )

    if not record:
        return False

    # Too many incorrect attempts.
    if record.get("attempts", 0) >= MAX_OTP_ATTEMPTS:
        return False

    # Handle MongoDB datetime correctly.
    expires_at = record["expires_at"]

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if datetime.now(timezone.utc) > expires_at:
        return False

    # Incorrect OTP.
    if record["code"] != submitted_code:
        otp_collection().update_one(
            {"user_id": user_id},
            {"$inc": {"attempts": 1}},
        )
        return False

    # Correct OTP.
    otp_collection().update_one(
        {"user_id": user_id},
        {"$set": {"verified": True}},
    )

    return True