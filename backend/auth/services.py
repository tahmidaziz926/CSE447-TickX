"""
auth/services.py — Business logic for registration, login, OTP, logout.

This layer has NO Flask/HTTP awareness — routes.py calls these
functions and translates results into HTTP responses. Keeping it
separate means these functions are independently testable, and
teammates can see exactly what registration/login DO without reading
Flask-specific code.
"""

from crypto import rsa, ecc
from security_logs import log_security_event
from crypto.hashing import hash_password, verify_password
from auth.models import build_user_document, find_user_by_email, insert_user, email_exists
from auth.otp import generate_otp, verify_otp
from auth.sessions import create_session


class AuthError(Exception):
    """Raised for any expected auth failure (bad input, wrong password,
    etc.) — routes.py catches this and returns a clean 4xx response."""
    pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(email: str, password: str, role: str, personal_info: dict) -> dict:
    """
    Registers a Buyer or Seller.

    personal_info: dict with sensitive fields to RSA-encrypt, e.g.
        {"name": "...", "phone": "...", "address": "..."}

    Returns basic (non-sensitive) info about the created account.
    """
    if role not in ("BUYER", "SELLER"):
        raise AuthError("role must be BUYER or SELLER")

    if not email or "@" not in email:
        raise AuthError("a valid email is required")

    if email_exists(email):
        raise AuthError("an account with this email already exists")

    if len(password) < 8:
        raise AuthError("password must be at least 8 characters")

    # 1. Generate this user's RSA key pair (from-scratch implementation)
    keypair = rsa.generate_keypair(bits=512)

    # 1b. Generate this user's ECC key pair (Person 2's from-scratch
    # implementation) — every registered Buyer/Seller gets one, per
    # Section 6.2 of the requirements. Used for ECC-signing their own
    # events/records later (e.g. Tahmid's event creation flow).
    ecc_keypair = ecc.generate_keypair()

    # 2. RSA-encrypt each sensitive personal info field
    encrypted_fields = {}
    for field_name, value in personal_info.items():
        cipher_chunks = rsa.encrypt_text(value, keypair["public"])
        encrypted_fields[field_name] = rsa.chunks_to_hex(cipher_chunks)

    # 3. Hash + salt the password (never store plaintext)
    hashed = hash_password(password)

    # 4. Build and insert the user document
    #    IMPORTANT: RSA keys and the ECC private key are integers far
    #    bigger than MongoDB's 8-byte int limit — they MUST be
    #    converted to hex strings before storage (rsa.key_to_dict /
    #    hex()), or insert_user() will raise an OverflowError. Convert
    #    back with rsa.key_from_dict() / int(x, 16) before using them
    #    for any actual crypto operation later (e.g. events/routes.py
    #    reading ecc_private_key to sign an event).
    user_doc = build_user_document(
        email=email,
        role=role,
        password_hash=hashed["hash"],
        password_salt=hashed["salt"],
        encrypted_fields=encrypted_fields,
        rsa_public_key=rsa.key_to_dict(keypair["public"]),
        rsa_private_key=rsa.key_to_dict(keypair["private"]),  # TODO: hand off to Key Management Module
        ecc_public_key=ecc.public_key_to_dict(ecc_keypair["public"]),
        ecc_private_key=hex(ecc_keypair["private"]),  # TODO: hand off to Key Management Module
    )
    user_id = insert_user(user_doc)

    return {
        "user_id": str(user_id),
        "email": email,
        "role": role,
        "seller_status": user_doc["seller_status"],
    }


# ---------------------------------------------------------------------------
# Login — step 1: password verification, triggers OTP
# ---------------------------------------------------------------------------

def login_step1_password(email: str, password: str) -> dict:
    """
    Verifies email + password. On success, generates and "sends" an
    OTP, and returns just enough info for the client to proceed to
    the OTP-verification step (NOT a full session yet).
    """
    user = find_user_by_email(email)
    if user is None:
        # Same generic error as a wrong password — don't reveal
        # whether the email exists at all (a common enumeration
        # protection). Still logged, but without a user_id since none
        # was matched.
        log_security_event("LOGIN_FAILED", f"Login attempt for unknown email", {"email": email})
        raise AuthError("invalid email or password")

    if not verify_password(password, user["password_hash"], user["password_salt"]):
        log_security_event(
            "LOGIN_FAILED", "Incorrect password", {"user_id": str(user["_id"]), "email": email}
        )
        raise AuthError("invalid email or password")

    if user.get("account_status") != "ACTIVE":
        log_security_event(
            "LOGIN_BLOCKED", "Login attempt on suspended/inactive account",
            {"user_id": str(user["_id"]), "email": email},
        )
        raise AuthError("account is suspended or inactive")

    generate_otp(user["_id"])  # prints to console for this project

    return {
        "user_id": str(user["_id"]),
        "message": "OTP sent. Please verify to complete login.",
    }


# ---------------------------------------------------------------------------
# Login — step 2: OTP verification, issues session
# ---------------------------------------------------------------------------

def login_step2_otp(user_id, submitted_code: str) -> dict:
    """
    Verifies the OTP. On success, creates a real session token —
    this is the only point at which a session is actually issued,
    matching Section 9: "A secure session will only be established
    after successful password verification and Two-Factor
    Authentication."
    """
    from bson import ObjectId
    from auth.models import users_collection

    if not verify_otp(user_id, submitted_code):
        log_security_event("OTP_FAILED", "Invalid or expired OTP submitted", {"user_id": str(user_id)})
        raise AuthError("invalid or expired OTP")

    user = users_collection().find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) else user_id})
    if user is None:
        raise AuthError("user not found")

    token = create_session(user["_id"], user["role"])

    return {
        "session_token": token,
        "role": user["role"],
        "email": user["email"],
    }


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def logout_user(token: str):
    from auth.sessions import invalidate_session
    invalidate_session(token)