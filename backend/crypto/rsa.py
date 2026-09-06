"""
rsa.py — RSA implemented from scratch (TixCrypt / Cryptix project, Person 1)

No use of any cryptographic library or high-level crypto API.
Uses Python's built-in arbitrary-precision integers and the `secrets`
module for cryptographically secure randomness.

Covers:
    - Primality testing (Miller-Rabin, implemented here)
    - Random prime generation
    - Extended Euclidean algorithm / modular inverse
    - RSA key pair generation
    - Encryption / decryption of arbitrary-length byte strings
    - RSA key serialization for MongoDB

Intended to be imported as:

    from crypto import rsa
"""

import secrets


# ---------------------------------------------------------------------------
# 1. Primality testing (Miller-Rabin)
# ---------------------------------------------------------------------------

# Small primes used to quickly reject obvious composite numbers.
_SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
    31, 37, 41, 43, 47, 53
]


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    """
    Miller-Rabin probabilistic primality test.
    """

    if n < 2:
        return False

    # Check divisibility by small primes first.
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    # Write n - 1 as:
    #
    #     n - 1 = 2^r * d
    #
    # where d is odd.
    d = n - 1
    r = 0

    while d % 2 == 0:
        d //= 2
        r += 1

    # Miller-Rabin test rounds.
    for _ in range(rounds):
        # Random a in range [2, n - 2].
        a = secrets.randbelow(n - 3) + 2

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


# ---------------------------------------------------------------------------
# 2. Prime generation
# ---------------------------------------------------------------------------

def generate_prime(bits: int) -> int:
    """
    Generate a random prime number with exactly `bits` bits.
    """

    if bits < 8:
        raise ValueError("bits must be >= 8")

    while True:
        # Generate a random integer.
        candidate = secrets.randbits(bits)

        # Force the highest bit so the number has exactly `bits` bits.
        # Force the lowest bit so the number is odd.
        candidate |= (1 << (bits - 1))
        candidate |= 1

        if is_probable_prime(candidate):
            return candidate


# ---------------------------------------------------------------------------
# 3. Extended Euclidean algorithm / modular inverse
# ---------------------------------------------------------------------------

def extended_gcd(a: int, b: int):
    """
    Returns:

        (gcd, x, y)

    such that:

        a*x + b*y = gcd
    """

    if b == 0:
        return a, 1, 0

    gcd, x1, y1 = extended_gcd(b, a % b)

    x = y1
    y = x1 - (a // b) * y1

    return gcd, x, y


def mod_inverse(e: int, phi: int) -> int:
    """
    Returns d such that:

        (e * d) % phi == 1
    """

    gcd, x, _ = extended_gcd(e, phi)

    if gcd != 1:
        raise ValueError(
            "modular inverse does not exist "
            "(e and phi are not coprime)"
        )

    return x % phi


# ---------------------------------------------------------------------------
# 4. RSA key generation
# ---------------------------------------------------------------------------

def generate_keypair(bits: int = 512) -> dict:
    """
    Generate an RSA key pair.

    `bits` is the size of EACH prime p and q.

    For example:

        bits = 512

    creates approximately a 1024-bit RSA modulus.

    Returns:

        {
            "public": {
                "e": e,
                "n": n
            },

            "private": {
                "d": d,
                "n": n
            }
        }
    """

    # Generate two different prime numbers.
    p = generate_prime(bits)

    q = generate_prime(bits)

    while p == q:
        q = generate_prime(bits)

    # RSA modulus.
    n = p * q

    # Euler's totient.
    phi = (p - 1) * (q - 1)

    # Standard RSA public exponent.
    e = 65537

    # In the unlikely event that 65537 is not coprime with phi,
    # find another odd value.
    if extended_gcd(e, phi)[0] != 1:
        e = 3

        while extended_gcd(e, phi)[0] != 1:
            e += 2

    # Calculate private exponent.
    d = mod_inverse(e, phi)

    return {
        "public": {
            "e": e,
            "n": n
        },

        "private": {
            "d": d,
            "n": n
        }
    }


# ---------------------------------------------------------------------------
# 5. Encryption / decryption helpers
# ---------------------------------------------------------------------------

def _key_byte_length(n: int) -> int:
    """
    Return the number of bytes required to represent n.
    """

    return (n.bit_length() + 7) // 8


# ---------------------------------------------------------------------------
# 6. RSA encryption
# ---------------------------------------------------------------------------

def encrypt_bytes(message: bytes, public_key: dict) -> list:
    """
    Encrypt arbitrary-length bytes using chunked RSA.

    Returns a list of ciphertext integers.
    """

    if not isinstance(message, bytes):
        raise TypeError("message must be bytes")

    if not isinstance(public_key, dict):
        raise TypeError("public_key must be a dictionary")

    if "e" not in public_key or "n" not in public_key:
        raise ValueError("public_key must contain 'e' and 'n'")

    e = public_key["e"]
    n = public_key["n"]

    # Ensure the values are integers.
    e = int(e)
    n = int(n)

    key_len = _key_byte_length(n)

    # A plaintext block must be smaller than n.
    max_chunk = key_len - 1

    if max_chunk <= 0:
        raise ValueError("Invalid RSA modulus")

    # Prefix the message with its original length.
    length_prefix = len(message).to_bytes(4, "big")

    data = length_prefix + message

    # Pad with zero bytes so every chunk has exactly max_chunk bytes.
    pad_len = (-len(data)) % max_chunk

    if pad_len:
        data += b"\x00" * pad_len

    # Split into chunks.
    chunks = [
        data[i:i + max_chunk]
        for i in range(0, len(data), max_chunk)
    ]

    ciphertext = []

    for chunk in chunks:
        plaintext_integer = int.from_bytes(chunk, "big")

        encrypted_integer = pow(
            plaintext_integer,
            e,
            n
        )

        ciphertext.append(encrypted_integer)

    return ciphertext


# ---------------------------------------------------------------------------
# 7. RSA decryption
# ---------------------------------------------------------------------------

def decrypt_bytes(cipher_chunks: list, private_key: dict) -> bytes:
    """
    Decrypt a list of RSA ciphertext integers.

    Returns the original plaintext bytes.
    """

    if not isinstance(cipher_chunks, list):
        raise TypeError("cipher_chunks must be a list")

    if not isinstance(private_key, dict):
        raise TypeError("private_key must be a dictionary")

    if "d" not in private_key or "n" not in private_key:
        raise ValueError("private_key must contain 'd' and 'n'")

    d = private_key["d"]
    n = private_key["n"]

    # Ensure the values are integers.
    d = int(d)
    n = int(n)

    key_len = _key_byte_length(n)

    max_chunk = key_len - 1

    if max_chunk <= 0:
        raise ValueError("Invalid RSA modulus")

    output = b""

    for ciphertext_integer in cipher_chunks:
        # Convert possible string values into integers.
        ciphertext_integer = int(ciphertext_integer)

        # RSA decryption.
        plaintext_integer = pow(
            ciphertext_integer,
            d,
            n
        )

        # Restore the fixed-size plaintext chunk.
        plaintext_chunk = plaintext_integer.to_bytes(
            max_chunk,
            "big"
        )

        output += plaintext_chunk

    # The first four bytes contain the original message length.
    if len(output) < 4:
        raise ValueError("Invalid ciphertext data")

    message_length = int.from_bytes(
        output[:4],
        "big"
    )

    # Return only the original message, removing padding.
    return output[4:4 + message_length]


# ---------------------------------------------------------------------------
# 8. Text encryption / decryption wrappers
# ---------------------------------------------------------------------------

def encrypt_text(message: str, public_key: dict) -> list:
    """
    Encrypt a UTF-8 string.

    Returns a list of ciphertext integers.
    """

    if not isinstance(message, str):
        raise TypeError("message must be a string")

    return encrypt_bytes(
        message.encode("utf-8"),
        public_key
    )


def decrypt_text(cipher_chunks: list, private_key: dict) -> str:
    """
    Decrypt ciphertext chunks back into a UTF-8 string.
    """

    decrypted_bytes = decrypt_bytes(
        cipher_chunks,
        private_key
    )

    return decrypted_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# 9. Ciphertext serialization helpers
# ---------------------------------------------------------------------------

def chunks_to_hex(cipher_chunks: list) -> list:
    """
    Convert ciphertext integers into hexadecimal strings.

    Useful for storing ciphertext in MongoDB.
    """

    if not isinstance(cipher_chunks, list):
        raise TypeError("cipher_chunks must be a list")

    return [
        hex(int(cipher_chunk))
        for cipher_chunk in cipher_chunks
    ]


def hex_to_chunks(hex_chunks: list) -> list:
    """
    Convert hexadecimal ciphertext strings back into integers.
    """

    if not isinstance(hex_chunks, list):
        raise TypeError("hex_chunks must be a list")

    return [
        int(hex_chunk, 16)
        for hex_chunk in hex_chunks
    ]


# ---------------------------------------------------------------------------
# 10. RSA key serialization for MongoDB
# ---------------------------------------------------------------------------

def key_to_dict(key: dict) -> dict:
    """
    Convert an RSA key into a MongoDB-safe dictionary.

    RSA values such as n and d can be much larger than MongoDB's
    supported integer range, so all integer values are stored as strings.

    Example:

        {"e": 65537, "n": 123456789...}

    becomes:

        {"e": "65537", "n": "123456789..."}
    """

    if not isinstance(key, dict):
        raise TypeError("RSA key must be a dictionary")

    if not key:
        raise ValueError("RSA key cannot be empty")

    return {
        str(name): str(value)
        for name, value in key.items()
    }


def key_from_dict(key_data: dict) -> dict:
    """
    Convert a MongoDB-stored RSA key back into a normal RSA key.

    Example:

        {"d": "123456789...", "n": "987654321..."}

    becomes:

        {"d": 123456789..., "n": 987654321...}
    """

    if not isinstance(key_data, dict):
        raise TypeError("Stored RSA key must be a dictionary")

    if not key_data:
        raise ValueError("Stored RSA key cannot be empty")

    converted_key = {}

    for name, value in key_data.items():
        try:
            converted_key[str(name)] = int(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid RSA key value for '{name}'"
            ) from exc

    return converted_key