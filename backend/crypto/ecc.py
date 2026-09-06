"""
crypto/ecc.py — ECC implemented from scratch (TixCrypt / Cryptix, Person 2)

No use of any cryptographic library (no `cryptography`, `ecdsa`,
`pycryptodome`, etc.) — only Python's built-in integer arithmetic and
`secrets` for randomness.

Curve: secp256k1.
"""

import secrets
import hashlib


# ---------------------------------------------------------------------------
# secp256k1 curve parameters
# ---------------------------------------------------------------------------

_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_A = 0
_B = 7

_GX = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
)

_GY = (
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
)

_N = (
    0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
)


# Point at infinity.
INFINITY = None


# Generator point.
G = (_GX, _GY)


# ---------------------------------------------------------------------------
# Private key conversion helper
# ---------------------------------------------------------------------------

def _normalize_private_key(private_key) -> int:
    """
    Convert a private key retrieved from storage into a Python integer.

    MongoDB-safe storage may store the ECC private key as:
        - an integer
        - a decimal string
        - a hexadecimal string

    This function converts supported formats into a normal Python int.
    """

    if isinstance(private_key, int):
        key = private_key

    elif isinstance(private_key, str):
        private_key = private_key.strip()

        if private_key.startswith(("0x", "0X")):
            key = int(private_key, 16)
        else:
            key = int(private_key, 10)

    else:
        raise TypeError(
            "ECC private key must be an integer or a string"
        )

    if not (1 <= key < _N):
        raise ValueError(
            "ECC private key must be in the range [1, N-1]"
        )

    return key


# ---------------------------------------------------------------------------
# Point arithmetic
# ---------------------------------------------------------------------------

def _mod_inverse(x: int, p: int) -> int:
    """
    Modular inverse using the extended Euclidean algorithm.
    """

    if x == 0:
        raise ZeroDivisionError("inverse of 0 does not exist")

    lm, hm = 1, 0
    low, high = x % p, p

    while low > 1:
        ratio = high // low
        nm = hm - lm * ratio
        new = high - low * ratio

        lm, low, hm, high = nm, new, lm, low

    return lm % p


def is_on_curve(point) -> bool:
    """
    Check whether a point satisfies the secp256k1 curve equation.
    """

    if point is INFINITY:
        return True

    x, y = point

    return (
        y * y - (x * x * x + _A * x + _B)
    ) % _P == 0


def point_add(p1, p2):
    """
    Elliptic curve point addition.
    """

    if p1 is INFINITY:
        return p2

    if p2 is INFINITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    # P + (-P) = infinity.
    if x1 == x2 and (y1 + y2) % _P == 0:
        return INFINITY

    # P + P.
    if p1 == p2:
        return point_double(p1)

    slope = (
        (y2 - y1)
        * _mod_inverse(x2 - x1, _P)
    ) % _P

    x3 = (
        slope * slope - x1 - x2
    ) % _P

    y3 = (
        slope * (x1 - x3) - y1
    ) % _P

    return (x3, y3)


def point_double(point):
    """
    Elliptic curve point doubling.
    """

    if point is INFINITY:
        return INFINITY

    x, y = point

    if y == 0:
        return INFINITY

    slope = (
        (3 * x * x + _A)
        * _mod_inverse(2 * y, _P)
    ) % _P

    x3 = (
        slope * slope - 2 * x
    ) % _P

    y3 = (
        slope * (x - x3) - y
    ) % _P

    return (x3, y3)


def scalar_multiply(k: int, point):
    """
    Scalar multiplication k * P using double-and-add.
    """

    k = int(k)

    if k % _N == 0 or point is INFINITY:
        return INFINITY

    result = INFINITY
    addend = point

    while k:
        if k & 1:
            result = point_add(
                result,
                addend,
            )

        addend = point_double(addend)

        k >>= 1

    return result


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def generate_keypair():
    """
    Generate an ECC key pair.

    Returns:

        {
            "private": private_key,
            "public": (x, y)
        }
    """

    private_key = (
        secrets.randbelow(_N - 1) + 1
    )

    public_key = scalar_multiply(
        private_key,
        G,
    )

    return {
        "private": private_key,
        "public": public_key,
    }


# ---------------------------------------------------------------------------
# ECDSA message hashing
# ---------------------------------------------------------------------------

def _hash_message(message: bytes) -> int:
    """
    Hash a message and convert it to an integer.
    """

    if not isinstance(message, bytes):
        raise TypeError(
            "message must be bytes"
        )

    digest = hashlib.sha256(
        message
    ).digest()

    return int.from_bytes(
        digest,
        "big",
    ) % _N


# ---------------------------------------------------------------------------
# ECDSA signing
# ---------------------------------------------------------------------------

def sign(message: bytes, private_key) -> tuple:
    """
    Sign a message using ECDSA.

    Returns:

        (r, s)
    """

    # IMPORTANT:
    # Convert MongoDB-stored string private keys back into integers.
    private_key = _normalize_private_key(
        private_key
    )

    z = _hash_message(
        message
    )

    while True:

        # Generate a secure random nonce.
        k = secrets.randbelow(
            _N - 1
        ) + 1

        point = scalar_multiply(
            k,
            G,
        )

        if point is INFINITY:
            continue

        r = point[0] % _N

        if r == 0:
            continue

        k_inv = _mod_inverse(
            k,
            _N,
        )

        s = (
            k_inv
            * (
                z + r * private_key
            )
        ) % _N

        if s == 0:
            continue

        return (
            r,
            s,
        )


# ---------------------------------------------------------------------------
# ECDSA verification
# ---------------------------------------------------------------------------

def verify(
    message: bytes,
    signature: tuple,
    public_key,
) -> bool:
    """
    Verify an ECDSA signature.
    """

    if not isinstance(signature, tuple):
        return False

    if len(signature) != 2:
        return False

    r, s = signature

    # Convert stored values to normal Python integers.
    r = int(r)
    s = int(s)

    if not (
        1 <= r < _N
        and 1 <= s < _N
    ):
        return False

    if not isinstance(
        public_key,
        tuple,
    ):
        return False

    if len(public_key) != 2:
        return False

    public_key = (
        int(public_key[0]),
        int(public_key[1]),
    )

    if not is_on_curve(public_key):
        return False

    z = _hash_message(
        message
    )

    s_inv = _mod_inverse(
        s,
        _N,
    )

    u1 = (
        z * s_inv
    ) % _N

    u2 = (
        r * s_inv
    ) % _N

    point = point_add(
        scalar_multiply(
            u1,
            G,
        ),
        scalar_multiply(
            u2,
            public_key,
        ),
    )

    if point is INFINITY:
        return False

    return (
        point[0] % _N
    ) == r


# ---------------------------------------------------------------------------
# Public key serialization
# ---------------------------------------------------------------------------

def public_key_to_dict(public_key) -> dict:
    """
    Convert an ECC public key point into a MongoDB-safe dictionary.
    """

    x, y = public_key

    return {
        "x": hex(int(x)),
        "y": hex(int(y)),
    }


def public_key_from_dict(data: dict):
    """
    Convert a stored public key dictionary back into an ECC point.
    """

    if not isinstance(data, dict):
        raise TypeError(
            "ECC public key data must be a dictionary"
        )

    return (
        int(data["x"], 16),
        int(data["y"], 16),
    )


# ---------------------------------------------------------------------------
# Private key serialization
# ---------------------------------------------------------------------------

def private_key_to_dict(private_key) -> dict:
    """
    Convert an ECC private key into a MongoDB-safe dictionary.

    The value is stored as a string because it is a large integer.
    """

    private_key = _normalize_private_key(
        private_key
    )

    return {
        "d": str(private_key),
    }


def private_key_from_dict(data: dict) -> int:
    """
    Convert a MongoDB-stored ECC private key dictionary
    back into a Python integer.
    """

    if not isinstance(data, dict):
        raise TypeError(
            "ECC private key data must be a dictionary"
        )

    if "d" not in data:
        raise ValueError(
            "ECC private key dictionary must contain 'd'"
        )

    return _normalize_private_key(
        data["d"]
    )


# ---------------------------------------------------------------------------
# Signature serialization
# ---------------------------------------------------------------------------

def signature_to_dict(signature: tuple) -> dict:
    """
    Convert an ECDSA signature into a MongoDB-safe dictionary.
    """

    r, s = signature

    return {
        "r": hex(int(r)),
        "s": hex(int(s)),
    }


def signature_from_dict(data: dict) -> tuple:
    """
    Convert a stored signature dictionary back into (r, s).
    """

    if not isinstance(data, dict):
        raise TypeError(
            "ECC signature data must be a dictionary"
        )

    return (
        int(data["r"], 16),
        int(data["s"], 16),
    )