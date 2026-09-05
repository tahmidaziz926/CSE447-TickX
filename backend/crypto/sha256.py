"""
crypto/sha256.py — SHA-256 implemented from scratch, per FIPS 180-4.
 
This closes the ambiguity flagged in hashing.py: instead of relying on
Python's hashlib.sha256 as the underlying primitive, this module
implements the actual SHA-256 compression function by hand — message
padding, the 64-round compression loop, and the standard round
constants — using only basic integer/bitwise operations.
 
No use of hashlib, hmac, or any cryptographic library anywhere in
this file.
 
Reference: NIST FIPS 180-4 (Secure Hash Standard).
"""
 
_MASK32 = 0xFFFFFFFF
 
# The first 32 bits of the fractional parts of the cube roots of the
# first 64 prime numbers (2..311). These are fixed constants defined
# by the SHA-256 standard itself, not something we "compute" — every
# conforming SHA-256 implementation uses these exact values.
_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]
 
# The first 32 bits of the fractional parts of the square roots of the
# first 8 prime numbers (2, 3, 5, 7, 11, 13, 17, 19) — the fixed
# initial hash state defined by the standard.
_H0 = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]
 
 
def _rotr(x: int, n: int) -> int:
    """32-bit right rotation."""
    return ((x >> n) | (x << (32 - n))) & _MASK32
 
 
def _pad(message: bytes) -> bytes:
    """
    SHA-256 padding: append a single '1' bit (as 0x80 since we work in
    whole bytes), then zero bits until the length is 448 mod 512 bits
    (56 mod 64 bytes), then the original message length as a 64-bit
    big-endian integer.
    """
    original_bit_length = len(message) * 8
    message += b"\x80"
    while len(message) % 64 != 56:
        message += b"\x00"
    message += original_bit_length.to_bytes(8, "big")
    return message
 
 
def sha256(message: bytes) -> bytes:
    """
    Compute the SHA-256 digest of `message`.
    Returns 32 raw bytes (the same output shape as hashlib.sha256(...).digest()).
    """
    h = list(_H0)
    padded = _pad(message)
 
    # process each 512-bit (64-byte) chunk
    for chunk_start in range(0, len(padded), 64):
        chunk = padded[chunk_start:chunk_start + 64]
 
        # break chunk into sixteen 32-bit big-endian words
        w = [0] * 64
        for i in range(16):
            w[i] = int.from_bytes(chunk[i * 4:i * 4 + 4], "big")
 
        # extend into 64 words total
        for i in range(16, 64):
            s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
            s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & _MASK32
 
        a, b, c, d, e, f, g, hh = h
 
        for i in range(64):
            S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            ch = (e & f) ^ ((~e & _MASK32) & g)
            temp1 = (hh + S1 + ch + _K[i] + w[i]) & _MASK32
 
            S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (S0 + maj) & _MASK32
 
            hh = g
            g = f
            f = e
            e = (d + temp1) & _MASK32
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & _MASK32
 
        h[0] = (h[0] + a) & _MASK32
        h[1] = (h[1] + b) & _MASK32
        h[2] = (h[2] + c) & _MASK32
        h[3] = (h[3] + d) & _MASK32
        h[4] = (h[4] + e) & _MASK32
        h[5] = (h[5] + f) & _MASK32
        h[6] = (h[6] + g) & _MASK32
        h[7] = (h[7] + hh) & _MASK32
 
    return b"".join(word.to_bytes(4, "big") for word in h)
 
 
def sha256_hexdigest(message: bytes) -> str:
    """Convenience wrapper returning the hex string form of the digest."""
    return sha256(message).hex()
 