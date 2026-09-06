"""
tests/test_admin.py — admin route RBAC + key management HTTP tests.

Uses the Flask test client (see conftest.py) to hit real routes, the
same way a browser/curl would, confirming role enforcement actually
happens at the HTTP layer (not just in application code that a route
might forget to call).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import auth_headers
from keys.service import get_or_create_active_key
from bson import ObjectId

def _make_pending_seller(mock_db, email="seller@test.com"):
    result = mock_db["users"].insert_one({
        "email": email,
        "role": "SELLER",
        "status": "PENDING",
        "personal_info": {"name": "Test Seller"},
    })
    return str(result.inserted_id)


def test_admin_can_list_pending_sellers(client, mock_db):
    _make_pending_seller(mock_db)
    headers = auth_headers(mock_db, "ADMIN")

    res = client.get("/api/admin/sellers/pending", headers=headers)
    assert res.status_code == 200
    assert len(res.get_json()) == 1


def test_admin_can_approve_seller(client, mock_db):
    seller_id = _make_pending_seller(mock_db)
    headers = auth_headers(mock_db, "ADMIN")

    res = client.post(f"/api/admin/sellers/{seller_id}/approve", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["status"] == "APPROVED"

    user = mock_db["users"].find_one({"_id": ObjectId(seller_id)})
    assert user["status"] == "APPROVED"


def test_admin_can_reject_seller(client, mock_db):
    seller_id = _make_pending_seller(mock_db)
    headers = auth_headers(mock_db, "ADMIN")

    res = client.post(f"/api/admin/sellers/{seller_id}/reject", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["status"] == "REJECTED"


def test_non_admin_cannot_approve_sellers(client, mock_db):
    seller_id = _make_pending_seller(mock_db)
    headers = auth_headers(mock_db, "BUYER")

    res = client.post(f"/api/admin/sellers/{seller_id}/approve", headers=headers)
    assert res.status_code == 403


def test_approving_nonexistent_seller_returns_404(client, mock_db):
    headers = auth_headers(mock_db, "ADMIN")
    fake_id = str(ObjectId())

    res = client.post(f"/api/admin/sellers/{fake_id}/approve", headers=headers)
    assert res.status_code == 404

def test_admin_routes_reject_unauthenticated_requests(client):
    res = client.get("/api/admin/users")
    assert res.status_code == 401


def test_admin_routes_reject_non_admin_roles(client, mock_db):
    for role in ("BUYER", "SELLER"):
        headers = auth_headers(mock_db, role)
        res = client.get("/api/admin/users", headers=headers)
        assert res.status_code == 403, f"{role} should be blocked from admin routes"


def test_admin_can_list_users(client, mock_db):
    headers = auth_headers(mock_db, "ADMIN")
    res = client.get("/api/admin/users", headers=headers)
    assert res.status_code == 200


def test_admin_can_view_security_logs(client, mock_db):
    headers = auth_headers(mock_db, "ADMIN")
    res = client.get("/api/admin/security-logs", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_non_admin_cannot_rotate_keys(client, mock_db):
    headers = auth_headers(mock_db, "SELLER")
    res = client.post("/api/admin/keys/rotate", json={"purpose": "ticket-mac"}, headers=headers)
    assert res.status_code == 403


def test_admin_can_rotate_keys(client, mock_db):
    get_or_create_active_key("ticket-mac")  # ensure version 1 exists
    headers = auth_headers(mock_db, "ADMIN")

    res = client.post("/api/admin/keys/rotate", json={"purpose": "ticket-mac"}, headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert body["new_version"] == 2
    assert body["status"] == "ACTIVE"


def test_rotate_requires_purpose_field(client, mock_db):
    headers = auth_headers(mock_db, "ADMIN")
    res = client.post("/api/admin/keys/rotate", json={}, headers=headers)
    assert res.status_code == 400


def test_admin_can_revoke_a_key(client, mock_db):
    key = get_or_create_active_key("ticket-mac")
    headers = auth_headers(mock_db, "ADMIN")

    res = client.post(f"/api/admin/keys/{key['_id']}/revoke", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["status"] == "REVOKED"


def test_admin_keys_endpoint_never_returns_key_material(client, mock_db):
    get_or_create_active_key("ticket-mac")
    headers = auth_headers(mock_db, "ADMIN")

    res = client.get("/api/admin/keys", headers=headers)
    assert res.status_code == 200
    for key in res.get_json():
        assert "key_material" not in key


def test_expired_session_is_rejected(client, mock_db):
    import secrets
    from datetime import datetime, timedelta, timezone

    expired_token = secrets.token_urlsafe(24)
    mock_db["sessions"].insert_one({
        "token": expired_token,
        "user_id": "someone",
        "role": "ADMIN",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "last_active": datetime.now(timezone.utc) - timedelta(hours=2),
        "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),  # already expired
    })

    res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401