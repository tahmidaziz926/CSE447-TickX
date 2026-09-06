"""
keys/models.py — Key Management Module: key metadata + lifecycle state.

Tracks algorithm, purpose, keyVersion, status, createdAt, rotatedAt,
revokedAt for every cryptographic key used by the system (the HMAC
secret keys used for MAC generation across profiles, events, tickets,
and transactions).

Private/secret key MATERIAL is stored here (hex string) but should
only ever be read by backend services — never exposed through any
user-facing API response. See keys/service.py for that enforcement.
"""

import secrets
from datetime import datetime, timezone
from extensions import get_db


def keys_collection():
    return get_db()["keys"]


def build_key_document(purpose: str, algorithm: str = "HMAC-SHA256", version: int = 1) -> dict:
    return {
        "purpose": purpose,  # e.g. "ticket-mac", "transaction-mac", "profile-mac", "event-mac"
        "algorithm": algorithm,
        "key_material": secrets.token_hex(32),  # 256-bit secret
        "key_version": version,
        "status": "ACTIVE",  # ACTIVE | ROTATED | REVOKED
        "created_at": datetime.now(timezone.utc),
        "rotated_at": None,
        "revoked_at": None,
    }


def insert_key(key_doc: dict):
    return keys_collection().insert_one(key_doc).inserted_id


def find_active_key(purpose: str):
    return keys_collection().find_one({"purpose": purpose, "status": "ACTIVE"})

def find_key_by_version(purpose: str, version: int):
    return keys_collection().find_one({"purpose": purpose, "key_version": version})


def find_key_by_id(key_id):
    return keys_collection().find_one({"_id": key_id})


def find_all_keys(purpose: str = None):
    query = {"purpose": purpose} if purpose else {}
    return list(keys_collection().find(query))


def mark_rotated(key_id):
    keys_collection().update_one(
        {"_id": key_id},
        {"$set": {"status": "ROTATED", "rotated_at": datetime.now(timezone.utc)}},
    )


def mark_revoked(key_id):
    keys_collection().update_one(
        {"_id": key_id},
        {"$set": {"status": "REVOKED", "revoked_at": datetime.now(timezone.utc)}},
    )