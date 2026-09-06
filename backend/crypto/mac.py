"""
crypto/mac.py — MAC (Message Authentication Code), TixCrypt Person 3.

Built entirely on crypto/sha256.py (Person 1's from-scratch SHA-256)
using our own HMAC construction (RFC 2104) — same technique as
crypto/hashing.py, but exposed here as a general-purpose MAC utility
for protecting any critical record (profiles, events, tickets,
transactions), per Section 6.4 of the requirements.

No use of hashlib or hmac anywhere in this file.
"""

from crypto.sha256 import sha256

_BLOCK_SIZE = 64  # SHA-256's internal block size, in bytes


def _hmac_sha256(key: bytes, message: bytes) -> bytes:
    """HMAC-SHA256 by hand, per RFC 2104."""
    if len(key) > _BLOCK_SIZE:
        key = sha256(key)
    key = key + b"\x00" * (_BLOCK_SIZE - len(key))

    ipad = bytes(b ^ 0x36 for b in key)
    opad = bytes(b ^ 0x5C for b in key)

    inner = sha256(ipad + message)
    return sha256(opad + inner)


def _constant_time_equal(a: bytes, b: bytes) -> bool:
    """Constant-time comparison — avoids leaking timing information
    about where a mismatch occurs."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def canonicalize(fields: dict) -> bytes:
    """
    Deterministic canonicalization of a record's protected fields.

    MUST produce the exact same bytes for the exact same logical data
    every time, or MAC verification will spuriously fail even when
    nothing was tampered with. Sorting keys makes this independent of
    dict insertion/iteration order (which Python does not guarantee
    identically across processes/versions for all cases).

    Values are converted with str() for a simple, predictable
    representation — every caller (tickets, transactions, profiles,
    events) must pass the SAME field values in the SAME form to both
    protect() and unprotect(), or verification will fail.
    """
    parts = [f"{k}={fields[k]}" for k in sorted(fields.keys())]
    return "|".join(parts).encode("utf-8")


def generate_mac(fields: dict, secret_key: bytes) -> str:
    """
    Generate a MAC over a record's protected fields.
    Returns a hex string, safe to store alongside the record in MongoDB.
    """
    message = canonicalize(fields)
    return _hmac_sha256(secret_key, message).hex()


def verify_mac(fields: dict, secret_key: bytes, stored_mac_hex: str) -> bool:
    """
    Recompute the MAC over `fields` and compare (constant-time)
    against the stored MAC.

    Returns False on ANY mismatch — including field tampering, wrong
    key, or a corrupted stored MAC. Per Section 6.4: "Any unauthorized
    modification of protected data should result in a failed MAC
    verification."
    """
    expected_hex = generate_mac(fields, secret_key)
    try:
        expected_bytes = bytes.fromhex(expected_hex)
        stored_bytes = bytes.fromhex(stored_mac_hex)
    except ValueError:
        return False  # malformed stored MAC — treat as verification failure
    return _constant_time_equal(expected_bytes, stored_bytes)