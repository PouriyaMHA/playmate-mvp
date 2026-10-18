"""Rate limits: per account for actions, per IP for public pages (main.check_rate)."""
import main


def test_likes_are_limited_per_account_and_recover(api, users, make_profile, db, monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(main, "_clock", lambda: now["t"])
    make_profile(users["alice"], "Alice")
    for i in range(60):   # liking a player who doesn't exist still counts as a request
        assert api.post("/api/like", user=users["alice"], json={"to_user": f"nobody{i}", "game": "cs2"})[0] == 404
    status, d = api.post("/api/like", user=users["alice"], json={"to_user": "nobody", "game": "cs2"})
    assert status == 429 and "slow down" in d["detail"]
    r = api.client.post("/api/like", json={"to_user": "x", "game": "cs2"},
                        headers={"Authorization": "Bearer " + __import__("conftest").make_token(users["alice"])})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    # another account isn't affected
    make_profile(users["bob"], "Bob")
    assert api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})[0] == 200
    now["t"] += 61   # a minute later it works again
    assert api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})[0] == 200


def test_hourly_cap_applies_even_when_spread_out(api, users, make_profile, monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(main, "_clock", lambda: now["t"])
    make_profile(users["alice"], "Alice")
    for i in range(600):
        now["t"] += 5   # 12 a minute: never hits the per-minute rule
        assert api.post("/api/like", user=users["alice"], json={"to_user": f"n{i}", "game": "cs2"})[0] == 404
    now["t"] += 5
    assert api.post("/api/like", user=users["alice"], json={"to_user": "n", "game": "cs2"})[0] == 429


def test_public_pages_are_limited_per_ip(api, users, make_profile, monkeypatch):
    monkeypatch.setattr(main, "_clock", lambda: 1000.0)
    make_profile(users["alice"], "Alice")
    ip = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    for _ in range(120):
        assert api.get("/api/public-profile?username=alice", headers=dict(ip))[0] == 200
    assert api.get("/api/public-profile?username=alice", headers=dict(ip))[0] == 429
    assert api.get("/api/public-profile?username=alice", headers={"X-Forwarded-For": "198.51.100.9"})[0] == 200


def test_unauthenticated_calls_are_401_not_counted(api):
    for _ in range(100):
        assert api.post("/api/like", json={"to_user": "x", "game": "cs2"})[0] == 401
    assert main._hits == {} or all(not k.startswith("like:") for k in main._hits)
