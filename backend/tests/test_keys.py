"""
tests/test_keys.py — keys/service.py + keys/models.py lifecycle tests.

Covers: first-key creation, rotation producing a new version, old
versions remaining valid for verifying old records, revocation
blocking an old version, and the "revoke the active key" edge case
that used to create a duplicate key_version=1 (see keys/service.py
revoke_key() docstring for the full explanation of the bug this
guards against).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keys.service import (
    get_or_create_active_key, get_key_material_for_verification,
    rotate_key, revoke_key, list_keys_for_admin, KeyLifecycleError,
)


def test_get_or_create_active_key_creates_version_1(mock_db):
    key = get_or_create_active_key("ticket-mac")
    assert key["key_version"] == 1
    assert key["status"] == "ACTIVE"
    assert key["purpose"] == "ticket-mac"


def test_get_or_create_active_key_returns_same_key_on_second_call(mock_db):
    first = get_or_create_active_key("ticket-mac")
    second = get_or_create_active_key("ticket-mac")
    assert first["_id"] == second["_id"]
    assert second["key_version"] == 1


def test_rotate_key_increments_version_and_deactivates_old(mock_db):
    original = get_or_create_active_key("ticket-mac")
    rotated = rotate_key("ticket-mac")

    assert rotated["key_version"] == original["key_version"] + 1
    assert rotated["status"] == "ACTIVE"

    # the new active key should now be what get_or_create_active_key returns
    current = get_or_create_active_key("ticket-mac")
    assert current["key_version"] == rotated["key_version"]


def test_old_key_version_still_verifies_after_rotation(mock_db):
    original = get_or_create_active_key("ticket-mac")
    rotate_key("ticket-mac")

    # version 1 material should still be retrievable for verifying
    # records that were MAC'd before the rotation happened
    material = get_key_material_for_verification("ticket-mac", original["key_version"])
    assert material == bytes.fromhex(original["key_material"])


def test_revoked_key_is_rejected_for_verification(mock_db):
    key = get_or_create_active_key("ticket-mac")
    revoke_key(key["_id"])

    try:
        get_key_material_for_verification("ticket-mac", key["key_version"])
        assert False, "expected KeyLifecycleError for a revoked key"
    except KeyLifecycleError:
        pass


def test_revoking_the_active_key_auto_rotates_first(mock_db):
    """
    Regression test for the bug where revoking the sole ACTIVE key
    left `purpose` with no active key, causing get_or_create_active_key()
    to mint a brand-new key at key_version=1 again — colliding with the
    just-revoked version 1.
    """
    original = get_or_create_active_key("ticket-mac")
    assert original["key_version"] == 1

    revoke_key(original["_id"])

    # a NEW active key must exist, at a HIGHER version — never a
    # duplicate/collision at version 1 again
    new_active = get_or_create_active_key("ticket-mac")
    assert new_active["status"] == "ACTIVE"
    assert new_active["key_version"] > original["key_version"]
    assert new_active["_id"] != original["_id"]

    # and the revoked version 1 must still be rejected
    try:
        get_key_material_for_verification("ticket-mac", 1)
        assert False, "expected version 1 to be rejected after revocation"
    except KeyLifecycleError:
        pass


def test_get_key_material_for_verification_raises_for_unknown_version(mock_db):
    get_or_create_active_key("ticket-mac")
    try:
        get_key_material_for_verification("ticket-mac", 999)
        assert False, "expected KeyLifecycleError for a version that doesn't exist"
    except KeyLifecycleError:
        pass


def test_list_keys_for_admin_never_exposes_key_material(mock_db):
    get_or_create_active_key("ticket-mac")
    rotate_key("ticket-mac")

    keys = list_keys_for_admin("ticket-mac")
    assert len(keys) == 2
    for k in keys:
        assert "key_material" not in k
        assert set(k.keys()) == {
            "key_id", "purpose", "algorithm", "key_version",
            "status", "created_at", "rotated_at", "revoked_at",
        }


def test_different_purposes_have_independent_key_versions(mock_db):
    ticket_key = get_or_create_active_key("ticket-mac")
    txn_key = get_or_create_active_key("transaction-mac")

    assert ticket_key["key_version"] == 1
    assert txn_key["key_version"] == 1
    assert ticket_key["_id"] != txn_key["_id"]

    rotate_key("ticket-mac")

    # rotating one purpose must not affect the other
    txn_current = get_or_create_active_key("transaction-mac")
    assert txn_current["key_version"] == 1