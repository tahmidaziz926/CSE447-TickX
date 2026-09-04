"""
extensions.py — shared infrastructure objects (DB client, etc.)
used across every teammate's feature modules.
"""

import certifi
from pymongo import MongoClient
from config import Config

_client = None
_db = None


def init_db():
    """Call this once, at app startup (from app.py)."""
    global _client, _db
    Config.validate()
    # tlsCAFile=certifi.where() fixes TLS handshake failures that happen
    # on some Windows Python installs when connecting to Atlas, caused by
    # an outdated/incomplete system CA certificate bundle.
    _client = MongoClient(Config.MONGODB_URI, tlsCAFile=certifi.where())
    _db = _client.get_database("cryptix")  # explicit db name
    return _db


def get_db():
    """Call this from anywhere (auth/services.py, events/, tickets/, etc.)
    to get the shared database handle."""
    if _db is None:
        raise RuntimeError("Database not initialized — call init_db() first in app.py")
    return _db