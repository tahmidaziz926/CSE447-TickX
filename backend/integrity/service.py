"""
integrity/service.py — Integrity middleware: protect() / unprotect().

Stable interface used by tickets/services.py (and available to
Tahmid's events code too, if wanted later) to protect critical
records. Ties together crypto/mac.py (the MAC primitive) and
keys/service.py (which secret key + version to use).
"""

from crypto.mac import generate_mac, verify_mac
from keys.service import (
    get_or_create_active_key, get_key_material_for_verification, KeyLifecycleError,
)
from security_logs import log_security_event


def protect(purpose: str, fields: dict) -> dict:
    """
    Generate a MAC over `fields` using the current active key for
    `purpose`. Returns {"mac": <hex>, "key_version": <int>} to store
    alongside the record.
    """
    key_doc = get_or_create_active_key(purpose)
    key_material = bytes.fromhex(key_doc["key_material"])
    mac = generate_mac(fields, key_material)
    return {"mac": mac, "key_version": key_doc["key_version"]}


def unprotect(purpose: str, fields: dict, stored_mac: str, key_version: int, context: dict = None) -> bool:
    """
    Verify a record's MAC before trusting it. On failure, writes a
    security log entry (Section 6.4 / Person 3's MAC ownership: "On
    verification failure, reject/flag the record and write a
    security-log event"). Returns True if intact, False otherwise.
    """
    try:
        key_material = get_key_material_for_verification(purpose, key_version)
    except KeyLifecycleError as e:
        log_security_event("MAC_KEY_ERROR", str(e), context)
        return False

    valid = verify_mac(fields, key_material, stored_mac)
    if not valid:
        log_security_event(
            "MAC_VERIFICATION_FAILED",
            f"MAC mismatch for purpose={purpose}",
            context,
        )
    return valid