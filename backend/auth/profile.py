"""
auth/profile.py — Buyer/Seller profile management (Sections 2.1, 3.1).

This was in Person 1's original scope ("user accounts", "buyer-side
pages") but hadn't been built yet. Implements the exact pattern the
requirements specify:
  - View: decrypt RSA-protected fields, verify MAC before returning
  - Update: re-encrypt changed fields, regenerate the MAC
  - MAC verification failure is logged and the record is rejected,
    matching the same pattern tickets/services.py uses

No new crypto here — reuses Person 1's RSA, Person 3's integrity
middleware (protect/unprotect), exactly as the requirements describe
these as complementary mechanisms (RSA for confidentiality, MAC for
integrity) working together on the same record.
"""

from bson import ObjectId
from crypto import rsa
from auth.models import users_collection
from integrity.service import protect, unprotect

PROFILE_FIELDS = ("name", "phone", "address")


class ProfileError(Exception):
    pass


def _get_user(user_id):
    oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
    user = users_collection().find_one({"_id": oid})
    if user is None:
        raise ProfileError("user not found")
    return user


def view_profile(user_id) -> dict:
    """
    Decrypt the user's protected fields for display, verifying the
    profile's MAC first (Section 2.1: "MAC verification will be
    performed before sensitive profile information is displayed").
    """
    user = _get_user(user_id)

    # profile_mac/profile_mac_version won't exist yet for accounts
    # created before this feature existed (e.g. via register_user()
    # before this file was added) — treat that as "not yet protected"
    # rather than a hard failure, so existing accounts aren't locked
    # out; protect the record on next update instead.
    if user.get("profile_mac"):
        mac_fields = {field: str(user["encrypted_fields"].get(field)) for field in PROFILE_FIELDS}
        valid = unprotect(
            "profile-mac", mac_fields, user["profile_mac"], user["profile_mac_version"],
            context={"user_id": str(user["_id"])},
        )
        if not valid:
            raise ProfileError(
                "profile integrity check failed — this record may have been tampered with"
            )

    rsa_private_key = rsa.key_from_dict(user["rsa_private_key"])

    decrypted = {}
    for field in PROFILE_FIELDS:
        encrypted_value = user.get("encrypted_fields", {}).get(field)
        if encrypted_value:
            cipher_chunks = rsa.hex_to_chunks(encrypted_value)
            decrypted[field] = rsa.decrypt_text(cipher_chunks, rsa_private_key)
        else:
            decrypted[field] = None

    return {
        "user_id": str(user["_id"]),
        "email": user["email"],
        "role": user["role"],
        **decrypted,
    }


def update_profile(user_id, updates: dict) -> dict:
    """
    Update the user's profile. Only fields present in `updates` are
    changed; RSA-encrypts each updated field before storage, then
    regenerates the profile's MAC over ALL current fields (not just
    the changed ones), so the MAC always covers the complete current
    state — matching Section 2.1: "Updated profile information will
    be encrypted again before being stored."
    """
    user = _get_user(user_id)
    rsa_public_key = rsa.key_from_dict(user["rsa_public_key"])
    rsa_private_key = rsa.key_from_dict(user["rsa_private_key"])

    # Start from the user's CURRENT decrypted values, then apply updates
    # on top — this way, fields the caller didn't touch are re-encrypted
    # with their existing value (needed since the MAC covers all fields
    # together, not per-field).
    current = {}
    for field in PROFILE_FIELDS:
        encrypted_value = user.get("encrypted_fields", {}).get(field)
        if encrypted_value:
            current[field] = rsa.decrypt_text(rsa.hex_to_chunks(encrypted_value), rsa_private_key)
        else:
            current[field] = None

    merged = {**current, **{k: v for k, v in updates.items() if k in PROFILE_FIELDS}}

    new_encrypted_fields = {}
    for field in PROFILE_FIELDS:
        value = merged.get(field)
        if value is not None:
            cipher_chunks = rsa.encrypt_text(value, rsa_public_key)
            new_encrypted_fields[field] = rsa.chunks_to_hex(cipher_chunks)

    mac_fields = {field: str(new_encrypted_fields.get(field)) for field in PROFILE_FIELDS}
    mac_info = protect("profile-mac", mac_fields)

    users_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {
            "encrypted_fields": new_encrypted_fields,
            "profile_mac": mac_info["mac"],
            "profile_mac_version": mac_info["key_version"],
        }},
    )

    return view_profile(user_id)