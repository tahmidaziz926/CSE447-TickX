"""
auth/models.py — User document shape + basic data-access helpers.

MongoDB is schemaless, so this module exists to keep the shape of a
"user" document consistent everywhere it's read/written, instead of
every file constructing dicts by hand with slightly different keys.
"""

from datetime import datetime, timezone
from extensions import get_db


def users_collection():
    return get_db()["users"]


def build_user_document(
    email: str,
    role: str,
    password_hash: str,
    password_salt: str,
    encrypted_fields: dict,
    rsa_public_key: dict,
    rsa_private_key: dict,
    ecc_public_key: dict = None,
) -> dict:
    """
    Shape of a user document stored in MongoDB.

    encrypted_fields: dict of RSA-encrypted personal info, e.g.
        {
            "name": [<cipher chunks>],
            "phone": [<cipher chunks>],
            "address": [<cipher chunks>],
        }
    (email is kept plaintext + indexed unique, since we need to look
    up users by email at login before any decryption can happen.)

    rsa_private_key is stored here for now as a placeholder — Person 3's
    Key Management Module owns the real secure storage/versioning of
    private keys. TODO: once that module exists, private keys should be
    written there instead of directly on the user document.
    """
    return {
        "email": email,
        "role": role,  # "BUYER" | "SELLER" | "ADMIN"
        "password_hash": password_hash,
        "password_salt": password_salt,
        "encrypted_fields": encrypted_fields,
        "rsa_public_key": rsa_public_key,
        "rsa_private_key": rsa_private_key,  # TODO: move to Key Management Module
        "ecc_public_key": ecc_public_key,    # filled in once Person 2's ECC keygen exists
        "seller_status": "PENDING" if role == "SELLER" else None,
        "account_status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
    }


def find_user_by_email(email: str):
    return users_collection().find_one({"email": email})


def insert_user(user_doc: dict):
    result = users_collection().insert_one(user_doc)
    return result.inserted_id


def email_exists(email: str) -> bool:
    return users_collection().count_documents({"email": email}, limit=1) > 0