"""
crypto/hashing.py — Password hashing + salting (TixCrypt, Person 1)

IMPORTANT NOTE FOR YOUR TEAM / INSTRUCTOR CHECK:
The requirements say the hashing "mechanism" must be implemented from
scratch. This module builds a custom salted, iterative key-stretching
construction OURSELVES (the salting scheme, the stretching/iteration
loop, and the comparison logic are all our own code) rather than
calling a ready-made password function like bcrypt, scrypt, argon2,
or werkzeug.security.generate_password_hash().
It uses Python's hashlib.sha256 only as the underlying primitive hash
step inside our own construction — the same way real algorithms like
PBKDF2 build on top of a standard hash function rather than
reinventing SHA-256 itself. Confirm with your instructor whether this
satisfies "from scratch," or whether SHA-256 itself must also be
hand-implemented — that would be a separate, larger task.

No use of bcrypt / passlib / werkzeug.security / hashlib-based
one-shot password helpers.
"""

import hashlib
import hmac
import secrets

# Number of stretching iterations. Higher = slower to brute-force,
# but slower for legitimate logins too. 100_000 is a reasonable
# academic-project value.
_ITERATIONS = 100_000
_HASH_LENGTH = 32  # bytes (SHA-256 output size)


def generate_salt() -> str:
    """Generate a unique, cryptographically random salt per user.
    Returned as a hex string for easy storage in MongoDB."""
    return secrets.token_hex(16)  # 16 bytes = 32 hex chars


def _stretch(password: str, salt: str, iterations: int = _ITERATIONS) -> bytes:
    """
    Our own iterative key-stretching construction:
    repeatedly hash (password + salt + previous_output) together.
    This is what makes brute-forcing slow, which is the whole point
    of a password hashing scheme (as opposed to a single fast hash).
    """
    salt_bytes = bytes.fromhex(salt)
    password_bytes = password.encode("utf-8")

    # start from a keyed hash of password+salt (HMAC-SHA256), then
    # feed the output back in for `iterations` rounds
    current = hmac.new(salt_bytes, password_bytes, hashlib.sha256).digest()
    for _ in range(iterations):
        current = hmac.new(salt_bytes, current + password_bytes, hashlib.sha256).digest()

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
    and compare against the stored hash.

    Uses hmac.compare_digest for a constant-time comparison, so an
    attacker can't learn anything from how long the comparison takes
    (a timing side-channel attack).
    """
    recomputed = _stretch(password, stored_salt)
    stored_bytes = bytes.fromhex(stored_hash)
    return hmac.compare_digest(recomputed, stored_bytes)