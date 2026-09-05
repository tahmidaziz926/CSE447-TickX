"""
auth/models.py — User document shape + basic data-access helpers.
"""

from datetime import datetime, timezone
from extensions import get_db


# MongoDB supports signed 64-bit integers only.
MAX_MONGO_INT = 2**63 - 1
MIN_MONGO_INT = -(2**63)


def users_collection():
    return get_db()["users"]


def make_mongo_safe(value):
    """
    Recursively converts integers that MongoDB cannot store
    into strings.

    RSA/ECC key components can be much larger than MongoDB's
    signed 64-bit integer limit.
    """

    if isinstance(value, dict):
        return {
            key: make_mongo_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            make_mongo_safe(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            make_mongo_safe(item)
            for item in value
        ]

    if isinstance(value, int):
        if value > MAX_MONGO_INT or value < MIN_MONGO_INT:
            return str(value)

    return value


def build_user_document(
    email: str,
    role: str,
    password_hash: str,
    password_salt: str,
    encrypted_fields: dict,
    rsa_public_key: dict,
    rsa_private_key: dict,
    ecc_public_key=None,
    ecc_private_key: int = None,
) -> dict:
    """
    Builds the user document.

    Large cryptographic integers are converted to strings because
    MongoDB only supports signed 64-bit integers.
    """

    return {
        "email": email,
        "role": role,

        "password_hash": password_hash,
        "password_salt": password_salt,

        "encrypted_fields": make_mongo_safe(encrypted_fields),

        "rsa_public_key": make_mongo_safe(rsa_public_key),
        "rsa_private_key": make_mongo_safe(rsa_private_key),

        "ecc_public_key": make_mongo_safe(ecc_public_key),
        "ecc_private_key": make_mongo_safe(ecc_private_key),

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
    return users_collection().count_documents(
        {"email": email},
        limit=1
    ) > 0