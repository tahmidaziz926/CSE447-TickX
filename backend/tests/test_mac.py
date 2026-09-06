"""
tests/test_mac.py — crypto/mac.py unit tests.

Covers: MAC round-trip correctness, tamper detection on every field,
wrong-key rejection, canonicalization order-independence, and
malformed stored-MAC handling.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.mac import generate_mac, verify_mac, canonicalize


SECRET = bytes.fromhex("a" * 64)  # 32-byte test key
OTHER_SECRET = bytes.fromhex("b" * 64)

SAMPLE_FIELDS = {
    "event_id": "evt123",
    "seat_number": 14,
    "buyer_id": "buyer456",
    "price": 500,
}


def test_generate_mac_returns_hex_string():
    mac = generate_mac(SAMPLE_FIELDS, SECRET)
    assert isinstance(mac, str)
    # 32-byte SHA-256 output -> 64 hex characters
    assert len(mac) == 64
    int(mac, 16)  # raises ValueError if not valid hex


def test_verify_mac_succeeds_for_untampered_record():
    mac = generate_mac(SAMPLE_FIELDS, SECRET)
    assert verify_mac(SAMPLE_FIELDS, SECRET, mac) is True


def test_verify_mac_fails_when_any_field_is_tampered():
    mac = generate_mac(SAMPLE_FIELDS, SECRET)

    for field_to_tamper in SAMPLE_FIELDS:
        tampered = dict(SAMPLE_FIELDS)
        if isinstance(tampered[field_to_tamper], int):
            tampered[field_to_tamper] += 1
        else:
            tampered[field_to_tamper] = str(tampered[field_to_tamper]) + "_tampered"

        assert verify_mac(tampered, SECRET, mac) is False, (
            f"tampering '{field_to_tamper}' should have failed verification"
        )


def test_verify_mac_fails_with_wrong_key():
    mac = generate_mac(SAMPLE_FIELDS, SECRET)
    assert verify_mac(SAMPLE_FIELDS, OTHER_SECRET, mac) is False


def test_verify_mac_fails_on_malformed_stored_mac():
    # Not valid hex at all
    assert verify_mac(SAMPLE_FIELDS, SECRET, "not-hex-zzz") is False
    # Valid hex but wrong length/value
    assert verify_mac(SAMPLE_FIELDS, SECRET, "00" * 32) is False


def test_canonicalize_is_order_independent():
    a = {"x": 1, "y": 2, "z": 3}
    b = {"z": 3, "x": 1, "y": 2}
    assert canonicalize(a) == canonicalize(b)


def test_canonicalize_distinguishes_different_values():
    a = canonicalize({"x": 1})
    b = canonicalize({"x": 2})
    assert a != b


def test_mac_is_deterministic_for_same_input():
    mac1 = generate_mac(SAMPLE_FIELDS, SECRET)
    mac2 = generate_mac(SAMPLE_FIELDS, SECRET)
    assert mac1 == mac2