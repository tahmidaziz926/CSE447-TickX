"""
auth/services.py — Business logic for registration, login, OTP, logout.

This layer has NO Flask/HTTP awareness — routes.py calls these
functions and translates results into HTTP responses.
"""

from crypto import rsa
from crypto.hashing import hash_password, verify_password
from auth.models import (
    build_user_document,
    find_user_by_email,
    insert_user,
    email_exists,
)
from auth.otp import generate_otp, verify_otp
from auth.sessions import create_session


class AuthError(Exception):
    """Raised for any expected authentication failure."""
    pass


# ---------------------------------------------------------------------------
# RSA Key Serialization Helpers
# ---------------------------------------------------------------------------

def serialize_key(key: dict) -> dict:
    """
    Convert large RSA integers into strings before storing them in MongoDB.

    MongoDB only supports integers up to 64-bit, while RSA key values
    can be hundreds of bits long.
    """
    return {
        name: str(value) if isinstance(value, int) else value
        for name, value in key.items()
    }


def deserialize_key(key: dict) -> dict:
    """
    Convert RSA key values stored as strings back into Python integers.

    Use this when retrieving an RSA key from MongoDB for cryptographic
    operations.
    """
    return {
        name: int(value) if isinstance(value, str) and value.lstrip("-").isdigit()
        else value
        for name, value in key.items()
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(email: str, password: str, role: str, personal_info: dict) -> dict:
    """
    Registers a Buyer or Seller.

    personal_info contains sensitive fields that will be RSA-encrypted.

    Example:
        {
            "name": "...",
            "phone": "...",
            "address": "..."
        }

    Returns basic non-sensitive information about the created account.
    """

    # Validate role
    if role not in ("BUYER", "SELLER"):
        raise AuthError("role must be BUYER or SELLER")

    # Validate email
    if not email or "@" not in email:
        raise AuthError("a valid email is required")

    # Check if email already exists
    if email_exists(email):
        raise AuthError("an account with this email already exists")

    # Validate password
    if len(password) < 8:
        raise AuthError("password must be at least 8 characters")

    # ---------------------------------------------------------------
    # 1. Generate this user's RSA key pair
    # ---------------------------------------------------------------

    keypair = rsa.generate_keypair(bits=512)

    # ---------------------------------------------------------------
    # 2. RSA-encrypt sensitive personal information
    # ---------------------------------------------------------------

    encrypted_fields = {}

    for field_name, value in personal_info.items():

        # Make sure the value is a string
        value = str(value)

        cipher_chunks = rsa.encrypt_text(
            value,
            keypair["public"]
        )

        # Convert encrypted chunks to hexadecimal strings
        encrypted_fields[field_name] = rsa.chunks_to_hex(
            cipher_chunks
        )

    # ---------------------------------------------------------------
    # 3. Hash and salt the password
    # ---------------------------------------------------------------

    hashed = hash_password(password)

    # ---------------------------------------------------------------
    # 4. Convert large RSA integers to strings for MongoDB
    # ---------------------------------------------------------------

    public_key_for_db = serialize_key(
        keypair["public"]
    )

    private_key_for_db = serialize_key(
        keypair["private"]
    )

    # ---------------------------------------------------------------
    # 5. Build user document
    # ---------------------------------------------------------------

    user_doc = build_user_document(
        email=email,
        role=role,
        password_hash=hashed["hash"],
        password_salt=hashed["salt"],
        encrypted_fields=encrypted_fields,
        rsa_public_key=public_key_for_db,
        rsa_private_key=private_key_for_db,
    )

    # ---------------------------------------------------------------
    # 6. Insert into MongoDB
    # ---------------------------------------------------------------

    user_id = insert_user(user_doc)

    # ---------------------------------------------------------------
    # 7. Return safe user information
    # ---------------------------------------------------------------

    return {
        "user_id": str(user_id),
        "email": email,
        "role": role,
        "seller_status": user_doc["seller_status"],
    }


# ---------------------------------------------------------------------------
# Login — Step 1: Password Verification
# ---------------------------------------------------------------------------

def login_step1_password(email: str, password: str) -> dict:
    """
    Verifies email and password.

    On success, generates an OTP.
    """

    user = find_user_by_email(email)

    if user is None:
        raise AuthError("invalid email or password")

    # Verify password
    if not verify_password(
        password,
        user["password_hash"],
        user["password_salt"],
    ):
        raise AuthError("invalid email or password")

    # Check account status
    if user.get("account_status") != "ACTIVE":
        raise AuthError("account is suspended or inactive")

    # Generate OTP
    generate_otp(user["_id"])

    return {
        "user_id": str(user["_id"]),
        "message": "OTP sent. Please verify to complete login.",
    }


# ---------------------------------------------------------------------------
# Login — Step 2: OTP Verification
# ---------------------------------------------------------------------------

def login_step2_otp(user_id, submitted_code: str) -> dict:
    """
    Verifies the OTP.

    On successful verification, creates a session token.
    """

    from bson import ObjectId
    from auth.models import users_collection

    # Verify OTP
    if not verify_otp(user_id, submitted_code):
        raise AuthError("invalid or expired OTP")

    # Convert string user ID to MongoDB ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    # Find user
    user = users_collection().find_one({
        "_id": user_id
    })

    if user is None:
        raise AuthError("user not found")

    # Create authenticated session
    token = create_session(
        user["_id"],
        user["role"],
    )

    return {
        "session_token": token,
        "role": user["role"],
        "email": user["email"],
    }


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def logout_user(token: str):
    """
    Invalidates the user's current session.
    """

    from auth.sessions import invalidate_session

    invalidate_session(token)