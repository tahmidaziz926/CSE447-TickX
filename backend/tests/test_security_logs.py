"""
tests/test_security_logs.py — security_logs.py + integrity-triggered
logging tests.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_logs import log_security_event, get_recent_logs
from integrity.service import protect, unprotect


def test_log_security_event_stores_all_fields(mock_db):
    log_security_event("TEST_EVENT", "something happened", {"key": "value"})

    logs = get_recent_logs()
    assert len(logs) == 1
    assert logs[0]["event_type"] == "TEST_EVENT"
    assert logs[0]["message"] == "something happened"
    assert logs[0]["context"] == {"key": "value"}
    assert "timestamp" in logs[0]


def test_get_recent_logs_orders_newest_first(mock_db):
    # Tiny sleeps guarantee distinct timestamps — three calls fired
    # back-to-back can otherwise land in the same microsecond and make
    # sort order ambiguous, which isn't what this test is checking.
    log_security_event("FIRST", "1st", {})
    time.sleep(0.01)
    log_security_event("SECOND", "2nd", {})
    time.sleep(0.01)
    log_security_event("THIRD", "3rd", {})

    logs = get_recent_logs()
    assert [l["event_type"] for l in logs] == ["THIRD", "SECOND", "FIRST"]


def test_get_recent_logs_respects_limit(mock_db):
    for i in range(5):
        log_security_event(f"EVENT_{i}", "msg", {})

    logs = get_recent_logs(limit=2)
    assert len(logs) == 2


def test_unprotect_failure_writes_a_log_entry(mock_db):
    fields = {"a": 1, "b": 2}
    mac_info = protect("test-purpose", fields)

    tampered = {"a": 999, "b": 2}
    valid = unprotect("test-purpose", tampered, mac_info["mac"], mac_info["key_version"])

    assert valid is False
    logs = get_recent_logs()
    assert any(l["event_type"] == "MAC_VERIFICATION_FAILED" for l in logs)


def test_unprotect_success_writes_no_failure_log(mock_db):
    fields = {"a": 1, "b": 2}
    mac_info = protect("test-purpose", fields)

    valid = unprotect("test-purpose", fields, mac_info["mac"], mac_info["key_version"])

    assert valid is True
    logs = get_recent_logs()
    assert not any(l["event_type"] == "MAC_VERIFICATION_FAILED" for l in logs)


def test_unprotect_with_unknown_key_version_logs_key_error(mock_db):
    fields = {"a": 1}
    protect("test-purpose", fields)  # creates version 1

    valid = unprotect("test-purpose", fields, "0" * 64, key_version=999)

    assert valid is False
    logs = get_recent_logs()
    assert any(l["event_type"] == "MAC_KEY_ERROR" for l in logs)