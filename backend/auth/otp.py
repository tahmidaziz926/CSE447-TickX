"""
auth/otp.py — OTP (One-Time Password) generation & verification.

Section 1.3 of the requirements: "After successful password
verification, users must complete Two-Factor Authentication (OTP
verification)." This module implements that second factor.

For this academic project, OTPs are printed to the Flask console
instead of actually being sent via SMS/email (no real SMS/email
provider is required by the spec). This is easy to swap for a real
provider later without changing the rest of the auth flow.
"""

import secrets
from datetime import datetime, timedelta, timezone
from extensions import get_db

OTP_LENGTH = 6
OTP_VALID_MINUTES = 5


def otp_collection():
    return get_db()["otp_challenges"]


def generate_otp(user_id) -> str:
    """
    Generate a new numeric OTP for a user, store it with an expiry,
    and return the OTP (so the caller can "send" it — here, print it).
    Any previous unexpired OTP for this user is invalidated.
    """
    code = "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_VALID_MINUTES)

    otp_collection().update_one(
        {"user_id": user_id},
        {"$set": {
            "code": code,
            "expires_at": expires_at,
            "verified": False,
            "attempts": 0,
        }},
        upsert=True,
    )

    # Simulated delivery — replace with real SMS/email integration later.
    print(f"[OTP] Code for user {user_id}: {code} (valid {OTP_VALID_MINUTES} min)")

    return code


MAX_OTP_ATTEMPTS = 5


def verify_otp(user_id, submitted_code: str) -> bool:
    """
    Verify a submitted OTP against the stored challenge.
    Rejects expired OTPs, wrong codes, and codes after too many
    failed attempts (basic brute-force protection).
    """
    record = otp_collection().find_one({"user_id": user_id})
    if not record:
        return False

    if record.get("attempts", 0) >= MAX_OTP_ATTEMPTS:
        return False

    if datetime.now(timezone.utc) > record["expires_at"].replace(tzinfo=timezone.utc):
        return False

    if record["code"] != submitted_code:
        otp_collection().update_one(
            {"user_id": user_id},
            {"$inc": {"attempts": 1}},
        )
        return False

    otp_collection().update_one(
        {"user_id": user_id},
        {"$set": {"verified": True}},
    )
    return True