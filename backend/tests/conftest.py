"""
tests/conftest.py — shared pytest fixtures.

Uses mongomock (an in-memory fake MongoDB) instead of the real Atlas
cluster, so tests:
  - run instantly, with no network dependency
  - never touch real/shared data
  - can run in CI or offline

`mock_db` monkeypatches extensions._db directly, which is what every
models.py file's xxx_collection() helper reads from get_db(). This
bypasses init_db() entirely (which requires real Mongo credentials).

`client` builds a Flask test app with the real blueprints registered,
so HTTP-level tests (admin auth, route status codes) work exactly
like the real app, just against the in-memory DB.
"""

import sys
import os
import pytest
import mongomock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extensions


@pytest.fixture
def mock_db():
    """A fresh in-memory MongoDB database for a single test."""
    fake_client = mongomock.MongoClient()
    fake_db = fake_client["cryptix_test"]

    extensions._db = fake_db
    yield fake_db
    extensions._db = None  # reset so tests never leak state into each other


@pytest.fixture
def app(mock_db):
    """A Flask app instance wired to the in-memory DB, without calling
    init_db() (which would require a real MONGODB_URI)."""
    from flask import Flask
    from auth.routes import auth_bp
    from events.routes import events_bp
    from tickets.routes import tickets_bp, transactions_bp
    from admin.routes import admin_bp

    flask_app = Flask(__name__)
    flask_app.config.update(TESTING=True)
    flask_app.register_blueprint(auth_bp, url_prefix="/api/auth")
    flask_app.register_blueprint(events_bp, url_prefix="/api/events")
    flask_app.register_blueprint(tickets_bp, url_prefix="/api/tickets")
    flask_app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    flask_app.register_blueprint(admin_bp, url_prefix="/api/admin")
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def make_session(mock_db, role: str, user_id="507f1f77bcf86cd799439011"):
    """
    Test helper: inserts a fake, already-authenticated session directly
    into the DB (skipping the real login/OTP flow, which isn't what
    these tests are checking) and returns a Bearer-ready token string.
    """
    import secrets
    from datetime import datetime, timedelta, timezone

    token = secrets.token_urlsafe(24)
    mock_db["sessions"].insert_one({
        "token": token,
        "user_id": user_id,
        "role": role,
        "created_at": datetime.now(timezone.utc),
        "last_active": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
    })
    return token


def auth_headers(mock_db, role: str, user_id="507f1f77bcf86cd799439011"):
    token = make_session(mock_db, role, user_id)
    return {"Authorization": f"Bearer {token}"}