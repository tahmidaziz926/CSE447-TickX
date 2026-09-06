"""
keys/service.py — Key lifecycle: generation, rotation, revocation.

Only backend services should ever call get_key_material_for_verification()
or get_or_create_active_key() — never expose raw key_material through
any API response. admin/routes.py exposes key METADATA only (version,
status, purpose, timestamps), never key_material.
"""

from bson import ObjectId
from keys.models import (
    build_key_document, insert_key, find_active_key, find_key_by_version,
    find_all_keys, mark_rotated, mark_revoked,
)


class KeyLifecycleError(Exception):
    pass


def get_or_create_active_key(purpose: str) -> dict:
    """Returns the current ACTIVE key for a purpose, creating the
    first version if none exists yet."""
    existing = find_active_key(purpose)
    if existing:
        return existing

    new_key = build_key_document(purpose, version=1)
    key_id = insert_key(new_key)
    new_key["_id"] = key_id
    return new_key


def get_key_material_for_verification(purpose: str, version: int) -> bytes:
    """
    Retrieve key material for verifying an OLDER record (signed with a
    previous key version). Rotated keys remain valid for verifying
    past records — only REVOKED keys are rejected entirely, which is
    what makes revocation stricter than rotation.
    """
    key_doc = find_key_by_version(purpose, version)
    if key_doc is None:
        raise KeyLifecycleError(f"no key found for purpose={purpose} version={version}")
    if key_doc["status"] == "REVOKED":
        raise KeyLifecycleError(f"key version {version} for '{purpose}' has been revoked")
    return bytes.fromhex(key_doc["key_material"])


def rotate_key(purpose: str) -> dict:
    """
    Generate a new key version for `purpose`, marking the previous
    ACTIVE key as ROTATED (it remains usable for verifying old
    records, but is never used for new MAC generation going forward).
    """
    current = find_active_key(purpose)
    next_version = (current["key_version"] + 1) if current else 1

    if current:
        mark_rotated(current["_id"])

    new_key = build_key_document(purpose, version=next_version)
    key_id = insert_key(new_key)
    new_key["_id"] = key_id
    return new_key


def revoke_key(key_id) -> None:
    """
    Admin-triggered revocation of a compromised/invalid key. Revoked
    keys are rejected for both new operations and future verification.
    """
    oid = key_id if isinstance(key_id, ObjectId) else ObjectId(key_id)
    mark_revoked(oid)


def list_keys_for_admin(purpose: str = None) -> list:
    """Returns key METADATA only (never key_material) — safe to
    expose through the admin dashboard."""
    keys = find_all_keys(purpose)
    result = []
    for k in keys:
        result.append({
            "key_id": str(k["_id"]),
            "purpose": k["purpose"],
            "algorithm": k["algorithm"],
            "key_version": k["key_version"],
            "status": k["status"],
            "created_at": k["created_at"].isoformat(),
            "rotated_at": k["rotated_at"].isoformat() if k.get("rotated_at") else None,
            "revoked_at": k["revoked_at"].isoformat() if k.get("revoked_at") else None,
        })
    return result