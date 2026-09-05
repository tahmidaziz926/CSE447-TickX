"""
crypto/hashing.py — Password hashing + salting (TixCrypt, Person 1)

Fully from scratch now: this module implements its own HMAC
construction and its own constant-time comparison, built entirely on
top of crypto/sha256.py (also implemented from scratch, per FIPS
180-4). No use of hashlib, hmac, bcrypt, passlib, or
werkzeug.security anywhere in this file or its dependencies.
"""

import secrets
from crypto.sha256 import sha256

_BLOCK_SIZE = 64  # SHA-256's internal block size, in bytes

# Stretching rounds. This is LOWER than a typical production value
# (real systems often use 100,000+ with hashlib, which is C-optimized
# and does that in milliseconds). Our SHA-256 is pure Python, roughly
# 100-1000x slower than hashlib's C implementation, so 100,000 rounds
# here would take ~30+ seconds per login attempt — unusable. 500 rounds
# takes ~0.4s, which is an acceptable login delay for this project.
# This is a genuine, worth-documenting tradeoff of doing SHA-256 "from
# scratch" in pure Python rather than relying on a compiled library.
_ITERATIONS = 500
_HASH_LENGTH = 32  # bytes (SHA-256 output size)


# ---------------------------------------------------------------------------
# Our own HMAC construction (RFC 2104), built on our own sha256()
# ---------------------------------------------------------------------------

def _hmac_sha256(key: bytes, message: bytes) -> bytes:
    """
    HMAC-SHA256, implemented by hand from the RFC 2104 definition:
        HMAC(K, m) = H( (K' xor opad) || H( (K' xor ipad) || m ) )
    where K' is the key padded/hashed to exactly one block length.
    """
    if len(key) > _BLOCK_SIZE:
        key = sha256(key)
    key = key + b"\x00" * (_BLOCK_SIZE - len(key))

    ipad = bytes(b ^ 0x36 for b in key)
    opad = bytes(b ^ 0x5C for b in key)

    inner = sha256(ipad + message)
    return sha256(opad + inner)


def _constant_time_equal(a: bytes, b: bytes) -> bool:
    """
    Our own constant-time byte comparison, so verification doesn't leak
    timing information about how many leading bytes matched (a timing
    side-channel attack). Always compares every byte regardless of
    where the first mismatch occurs.
    """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


# ---------------------------------------------------------------------------
# Salting + key stretching
# ---------------------------------------------------------------------------

def generate_salt() -> str:
    """Generate a unique, cryptographically random salt per user.
    Returned as a hex string for easy storage in MongoDB."""
    return secrets.token_hex(16)  # 16 bytes = 32 hex chars


def _stretch(password: str, salt: str, iterations: int = _ITERATIONS) -> bytes:
    """
    Our own iterative key-stretching construction: repeatedly HMAC
    (password + previous_output) keyed by the salt. This is what makes
    brute-forcing slow, which is the whole point of a password hashing
    scheme (as opposed to a single fast hash).
    """
    salt_bytes = bytes.fromhex(salt)
    password_bytes = password.encode("utf-8")

    current = _hmac_sha256(salt_bytes, password_bytes)
    for _ in range(iterations):
        current = _hmac_sha256(salt_bytes, current + password_bytes)

    return current  # 32 raw bytes


def hash_password(password: str, salt: str = None) -> dict:
    """
    Hash a plaintext password.

    If `salt` is not provided, generates a new unique salt (use this
    path at REGISTRATION time). If `salt` IS provided, hashes against
    that existing salt (use this path at LOGIN time, passing the
    salt you stored for that user).

    Returns {"hash": <hex string>, "salt": <hex string>}.
    """
    if salt is None:
        salt = generate_salt()

    digest = _stretch(password, salt)
    return {
        "hash": digest.hex(),
        "salt": salt,
    }


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verify a login attempt: recompute the hash using the stored salt,
    and compare against the stored hash using a constant-time comparison.
    """
    recomputed = _stretch(password, stored_salt)
    stored_bytes = bytes.fromhex(stored_hash)
    return _constant_time_equal(recomputed, stored_bytes)