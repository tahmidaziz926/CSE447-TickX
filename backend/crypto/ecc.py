"""
crypto/ecc.py — ECC implemented from scratch (TixCrypt / Cryptix, Person 2)

No use of any cryptographic library (no `cryptography`, `ecdsa`,
`pycryptodome`, etc.) — only Python's built-in integer arithmetic and
`secrets` for randomness.

Curve: secp256k1 — a standard, well-documented curve (the same one
Bitcoin uses). Using a standard curve's fixed public parameters (a, b,
p, G, n) is normal practice; what's implemented "from scratch" here is
the actual POINT ARITHMETIC (addition, doubling, scalar multiplication)
and the ECDSA signing/verification built on top of it — not the curve
parameters themselves, which are public constants anyone can look up
(the same way RSA doesn't require you to invent modular exponentiation
notation, just implement it).

Higher-level operation implemented: ECDSA (Elliptic Curve Digital
Signature Algorithm) — used for signing data to prove authenticity,
e.g. a seller's event listing, or a critical record's integrity,
separate from Person 1's RSA which handles encryption of personal
data. This gives RSA and ECC clearly distinct roles, as the
requirements ask for.

CONFIRM WITH YOUR INSTRUCTOR: exactly which application operation ECC
should be used for (a digital signature scheme, as implemented here,
vs. a key-agreement scheme like ECDH) — the requirements say "such as
digital signatures or key-related operations," leaving the exact
choice to your team.
"""

import secrets
import hashlib  # only used to hash the *message* being signed before
                 # the ECDSA math runs on it — this is standard: ECDSA
                 # always signs a hash of the message, never the raw
                 # message directly. If your team wants this to also
                 # avoid hashlib entirely, swap this for
                 # crypto.sha256.sha256 from Person 1's module.

# ---------------------------------------------------------------------------
# secp256k1 curve parameters (public, standard — not something to
# "compute" any more than RSA's use of prime numbers is computed from
# nothing) — curve equation: y^2 = x^3 + a*x + b (mod p)
# ---------------------------------------------------------------------------

_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_A = 0
_B = 7
_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# The point at infinity (the curve's "zero" / identity element),
# represented as None throughout this module.
INFINITY = None


# ---------------------------------------------------------------------------
# Point arithmetic — implemented from scratch
# ---------------------------------------------------------------------------

def _mod_inverse(x: int, p: int) -> int:
    """Modular inverse via the extended Euclidean algorithm (same
    technique as Person 1's RSA module, applied here mod p instead of
    mod phi(n))."""
    if x == 0:
        raise ZeroDivisionError("inverse of 0 does not exist")
    lm, hm = 1, 0
    low, high = x % p, p
    while low > 1:
        ratio = high // low
        nm, new = hm - lm * ratio, high - low * ratio
        lm, low, hm, high = nm, new, lm, low
    return lm % p


def is_on_curve(point) -> bool:
    """Validate that a point actually satisfies y^2 = x^3 + a*x + b (mod p)."""
    if point is INFINITY:
        return True
    x, y = point
    return (y * y - (x * x * x + _A * x + _B)) % _P == 0


def point_add(p1, p2):
    """
    Elliptic curve point addition, with the required special cases:
      - adding the point at infinity to anything returns the other point
      - adding a point to its own negation returns the point at infinity
      - adding a point to itself uses the doubling formula instead
    """
    if p1 is INFINITY:
        return p2
    if p2 is INFINITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and (y1 + y2) % _P == 0:
        # P + (-P) = point at infinity
        return INFINITY

    if p1 == p2:
        return point_double(p1)

    # standard point addition formula
    slope = ((y2 - y1) * _mod_inverse(x2 - x1, _P)) % _P
    x3 = (slope * slope - x1 - x2) % _P
    y3 = (slope * (x1 - x3) - y1) % _P
    return (x3, y3)


def point_double(point):
    """
    Elliptic curve point doubling (P + P), with the special case that
    doubling a point whose y-coordinate is 0 returns the point at
    infinity (the tangent line there is vertical).
    """
    if point is INFINITY:
        return INFINITY

    x, y = point
    if y == 0:
        return INFINITY

    slope = ((3 * x * x + _A) * _mod_inverse(2 * y, _P)) % _P
    x3 = (slope * slope - 2 * x) % _P
    y3 = (slope * (x - x3) - y) % _P
    return (x3, y3)


def scalar_multiply(k: int, point):
    """
    Scalar multiplication k*P via the double-and-add algorithm —
    the elliptic-curve equivalent of RSA's square-and-multiply for
    modular exponentiation.
    """
    if k % _N == 0 or point is INFINITY:
        return INFINITY

    result = INFINITY
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_double(addend)
        k >>= 1

    return result


G = (_GX, _GY)  # the curve's base/generator point


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def generate_keypair():
    """
    Generate an ECC key pair.
    Private key: a random integer in [1, n-1].
    Public key: privateKey * G (a point on the curve).

    Returns {"private": <int>, "public": (x, y)}.
    """
    private_key = secrets.randbelow(_N - 1) + 1
    public_key = scalar_multiply(private_key, G)
    return {"private": private_key, "public": public_key}


# ---------------------------------------------------------------------------
# ECDSA — the higher-level application operation built on the above
# ---------------------------------------------------------------------------

def _hash_message(message: bytes) -> int:
    """Hash the message and reduce it to an integer mod n, as ECDSA requires."""
    digest = hashlib.sha256(message).digest()
    return int.from_bytes(digest, "big") % _N


def sign(message: bytes, private_key: int) -> tuple:
    """
    ECDSA signing. Returns (r, s) — the signature.
    Uses a freshly random nonce k for every signature (reusing k, or
    using a predictable k, is what breaks ECDSA in practice — this is
    a well-known real-world pitfall worth mentioning in your report).
    """
    z = _hash_message(message)

    while True:
        k = secrets.randbelow(_N - 1) + 1
        point = scalar_multiply(k, G)
        if point is INFINITY:
            continue
        r = point[0] % _N
        if r == 0:
            continue

        k_inv = _mod_inverse(k, _N)
        s = (k_inv * (z + r * private_key)) % _N
        if s == 0:
            continue

        return (r, s)


def verify(message: bytes, signature: tuple, public_key) -> bool:
    """
    ECDSA verification. Returns True if `signature` is a valid
    signature over `message` under `public_key`.
    """
    r, s = signature
    if not (1 <= r < _N and 1 <= s < _N):
        return False

    z = _hash_message(message)
    s_inv = _mod_inverse(s, _N)

    u1 = (z * s_inv) % _N
    u2 = (r * s_inv) % _N

    point = point_add(scalar_multiply(u1, G), scalar_multiply(u2, public_key))
    if point is INFINITY:
        return False

    return (point[0] % _N) == r


# ---------------------------------------------------------------------------
# Serialization helpers (for storing keys/signatures in MongoDB)
# ---------------------------------------------------------------------------

def public_key_to_dict(public_key) -> dict:
    x, y = public_key
    return {"x": hex(x), "y": hex(y)}


def public_key_from_dict(data: dict):
    return (int(data["x"], 16), int(data["y"], 16))


def signature_to_dict(signature: tuple) -> dict:
    r, s = signature
    return {"r": hex(r), "s": hex(s)}


def signature_from_dict(data: dict) -> tuple:
    return (int(data["r"], 16), int(data["s"], 16))