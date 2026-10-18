"""Test setup: the app runs against an in-memory fake database (tests/fakedb.py) — never the real Supabase.

Dummy settings are put in the environment BEFORE main is imported; load_dotenv() never overrides variables that
are already set, so the real .env values can't leak into a test run.
"""
import os
import sys
import time
from pathlib import Path

import jwt
import pytest

TEST_SECRET = "test-jwt-secret-that-is-at-least-32-bytes"
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "test-service-key"
os.environ["SUPABASE_JWT_SECRET"] = TEST_SECRET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402
from fakedb import FakeSupabase  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

assert main.SUPABASE_URL == "https://example.supabase.co" and main.SUPABASE_JWT_SECRET == TEST_SECRET, \
    "tests must never run with the real Supabase settings"


def make_token(uid, **claims):
    body = {"sub": uid, "aud": "authenticated", "exp": int(time.time()) + 600, **claims}
    body = {k: v for k, v in body.items() if v is not None}
    return jwt.encode(body, TEST_SECRET, algorithm="HS256")


class Api:
    """Small wrapper: api.post("/api/like", user=alice, json={...}) -> (status, json)."""

    def __init__(self, client):
        self.client = client

    def call(self, method, path, user=None, token=None, **kw):
        headers = kw.pop("headers", {})
        if user or token:
            headers["Authorization"] = "Bearer " + (token or make_token(user))
        r = self.client.request(method, path, headers=headers, **kw)
        try:
            body = r.json()
        except ValueError:
            body = None
        return r.status_code, body

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, **kw):
        return self.call("POST", path, **kw)

    def put(self, path, **kw):
        return self.call("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.call("DELETE", path, **kw)


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(main, "supabase", fake)
    main._cache.clear()   # cached counters from another test must not leak in
    return fake


@pytest.fixture
def api(db):
    return Api(TestClient(main.app))


@pytest.fixture
def users(db):
    """Three auth users: alice, bob, carol (ids)."""
    return {name: db.auth.admin.create_user(email=f"{name}@example.com") for name in ("alice", "bob", "carol")}


BASE_PROFILE = {"region": "middle-east", "country": "Iran", "city": "Tehran", "mic": "voice", "languages": "fa,en"}


@pytest.fixture
def make_profile(api):
    def _make(user, name, game="cs2", **over):
        fields = over.pop("fields", None) or {
            "cs2": {"mode": "Premier", "rank": "Gold Nova"},
            "battlefield": {"favorite_mode": "Conquest", "class_type": "Assault"},
            "gta": {"activity": "Heists", "style": "Casual / fun"},
            "minecraft": {"edition": "Java", "mode": "Survival", "style": "Builder"},
            "lol": {"server": "EUW", "role": "Mid", "rank": "Gold"},
            "fc": {"mode": "Clubs", "division": "Div 4–2"},
        }[game]
        platform = over.pop("platform", None) or {"cs2": "PC", "lol": "PC", "gta": "PC (Enhanced)"}.get(game, "PC")
        body = {**BASE_PROFILE, "username": name, "game": game, "platform": platform, "fields": fields, **over}
        status, data = api.post("/api/profile", user=user, json=body)
        assert status == 200, data
        return data
    return _make


@pytest.fixture(autouse=True)
def _accounts_table_state(monkeypatch):
    """Every test starts with the accounts table "present" (the fake DB has it); tests can switch it off."""
    monkeypatch.setitem(main._accounts_check, "ok", False)
    monkeypatch.setitem(main._accounts_check, "at", -1e9)
