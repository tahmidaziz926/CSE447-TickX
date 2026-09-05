"""
rsa.py — RSA implemented from scratch (TixCrypt / Cryptix project, Person 1)

No use of any cryptographic library or high-level crypto API.
Only Python's built-in `random` module is used for randomness (not for
number theory / primality logic) and `secrets` for cryptographically
secure randomness where it matters.

Covers:
    - Primality testing (Miller-Rabin, implemented here)
    - Random prime generation
    - Extended Euclidean algorithm / modular inverse
    - RSA key pair generation
    - Encryption / decryption of arbitrary-length byte strings (chunked)

Intended to be imported as a module from Flask routes, e.g.:

    from rsa import generate_keypair, encrypt_text, decrypt_text
"""

import secrets

# ---------------------------------------------------------------------------
# 1. Primality testing (Miller-Rabin) — implemented from scratch
# ---------------------------------------------------------------------------

# Small primes used to quickly reject obvious composites before running
# the more expensive Miller-Rabin rounds.
_SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    """
    Miller-Rabin probabilistic primality test.

    With `rounds=40`, the probability of a composite number being
    misclassified as prime is astronomically small (roughly 4^-40),
    which is the standard used by real cryptographic libraries.
    """
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    # write n - 1 as 2^r * d with d odd
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1

    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2  # random a in [2, n-2]
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_prime(bits: int) -> int:
    """
    Generate a random prime number with exactly `bits` bits, using our
    own Miller-Rabin test (no sympy / no external number theory library).
    """
    if bits < 8:
        raise ValueError("bits must be >= 8")
    while True:
        candidate = secrets.randbits(bits)
        # force the top bit (so the number has exactly `bits` bits)
        # and the bottom bit (so it's odd, since even numbers > 2 aren't prime)
        candidate |= (1 << (bits - 1)) | 1
        if is_probable_prime(candidate):
            return candidate


# ---------------------------------------------------------------------------
# 2. Extended Euclidean algorithm / modular inverse
# ---------------------------------------------------------------------------

def extended_gcd(a: int, b: int):
    """Returns (gcd, x, y) such that a*x + b*y = gcd."""
    if b == 0:
        return a, 1, 0
    gcd, x1, y1 = extended_gcd(b, a % b)
    x = y1
    y = x1 - (a // b) * y1
    return gcd, x, y


def mod_inverse(e: int, phi: int) -> int:
    """Returns d such that (e * d) % phi == 1, or raises if none exists."""
    gcd, x, _ = extended_gcd(e, phi)
    if gcd != 1:
        raise ValueError("modular inverse does not exist (e and phi are not coprime)")
    return x % phi


# ---------------------------------------------------------------------------
# 3. Key generation
# ---------------------------------------------------------------------------

def generate_keypair(bits: int = 512):
    """
    Generate an RSA key pair.

    `bits` is the size of EACH prime (p and q), so the resulting modulus
    n is roughly 2*bits bits long. 512 bits per prime -> ~1024-bit key,
    which is a reasonable size for this project (bigger = slower keygen
    and slower encrypt/decrypt with no real security benefit here).

    Returns a dict:
        {
            "public":  {"e": e, "n": n},
            "private": {"d": d, "n": n},
        }
    Only ever store/transmit the private half through your Key
    Management Module — never expose it to the frontend.
    """
    p = generate_prime(bits)
    q = generate_prime(bits)
    while p == q:
        q = generate_prime(bits)

    n = p * q
    phi = (p - 1) * (q - 1)

    # Standard choice: try 65537 first (fast, widely used), fall back to
    # a random odd candidate if it happens not to be coprime with phi.
    e = 65537
    if extended_gcd(e, phi)[0] != 1:
        e = 3
        while extended_gcd(e, phi)[0] != 1:
            e += 2

    d = mod_inverse(e, phi)

    return {
        "public": {"e": e, "n": n},
        "private": {"d": d, "n": n},
    }


# ---------------------------------------------------------------------------
# 4. Encrypt / decrypt — chunked, so arbitrary-length text is supported
# ---------------------------------------------------------------------------
#
# Textbook RSA can only encrypt an integer smaller than n. A name, email,
# phone number, or address won't reliably fit in one block, so we:
#   1. Prefix the plaintext with its length (4 bytes, big-endian)
#   2. Split into fixed-size chunks that are guaranteed smaller than n
#   3. RSA-encrypt each chunk independently
#   4. On decrypt, reverse the process and use the length prefix to
#      strip any padding introduced by chunk alignment.

def _key_byte_length(n: int) -> int:
    return (n.bit_length() + 7) // 8


def encrypt_bytes(message: bytes, public_key: dict) -> list:
    """Encrypts arbitrary-length bytes. Returns a list of ciphertext ints."""
    e, n = public_key["e"], public_key["n"]
    key_len = _key_byte_length(n)
    max_chunk = key_len - 1  # stay strictly less than n

    length_prefix = len(message).to_bytes(4, "big")
    data = length_prefix + message

    # Pad data so its length is an exact multiple of max_chunk. This is
    # essential: decrypt_bytes reconstructs every chunk as exactly
    # max_chunk bytes (via to_bytes(max_chunk, "big")), which LEFT-pads
    # with zeros. If the final chunk here were shorter than max_chunk,
    # its real bytes would land at the END after decryption's fixed-
    # length reconstruction instead of the position they were encrypted
    # from — corrupting (or silently zeroing) the message. Padding here
    # guarantees every encrypted chunk is already exactly max_chunk
    # bytes, so decryption's reconstruction lines up exactly.
    pad_len = (-len(data)) % max_chunk
    data += b"\x00" * pad_len

    chunks = [data[i:i + max_chunk] for i in range(0, len(data), max_chunk)]
    return [pow(int.from_bytes(chunk, "big"), e, n) for chunk in chunks]


def decrypt_bytes(cipher_chunks: list, private_key: dict) -> bytes:
    """Reverses encrypt_bytes. Returns the original plaintext bytes."""
    d, n = private_key["d"], private_key["n"]
    key_len = _key_byte_length(n)
    max_chunk = key_len - 1

    out = b""
    for c in cipher_chunks:
        m = pow(c, d, n)
        out += m.to_bytes(max_chunk, "big")

    msg_len = int.from_bytes(out[:4], "big")
    return out[4:4 + msg_len]


def encrypt_text(message: str, public_key: dict) -> list:
    """Convenience wrapper for encrypting a UTF-8 string (e.g. a name/email)."""
    return encrypt_bytes(message.encode("utf-8"), public_key)


def decrypt_text(cipher_chunks: list, private_key: dict) -> str:
    """Convenience wrapper for decrypting back to a UTF-8 string."""
    return decrypt_bytes(cipher_chunks, private_key).decode("utf-8")


# For storage in MongoDB, ciphertext ints need to become strings.
def chunks_to_hex(cipher_chunks: list) -> list:
    return [hex(c) for c in cipher_chunks]


def hex_to_chunks(hex_chunks: list) -> list:
    return [int(h, 16) for h in hex_chunks]