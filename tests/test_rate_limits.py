"""Rate limits: per account for actions and private reads, per IP for public pages (main.check_rate)."""
import threading

import pytest
from fastapi import HTTPException

import main
from conftest import make_token


@pytest.fixture
def clock(monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(main, "_clock", lambda: now["t"])
    main._hits.clear()
    main._last_sweep[0] = now["t"]
    return now


def test_likes_are_limited_per_account_and_recover(api, users, make_profile, clock):
    make_profile(users["alice"], "Alice")
    for i in range(60):   # liking a player who doesn't exist still counts as a request
        assert api.post("/api/like", user=users["alice"], json={"to_user": f"nobody{i}", "game": "cs2"})[0] == 404
    status, d = api.post("/api/like", user=users["alice"], json={"to_user": "nobody", "game": "cs2"})
    assert status == 429 and "slow down" in d["detail"]
    r = api.client.post("/api/like", json={"to_user": "x", "game": "cs2"},
                        headers={"Authorization": "Bearer " + make_token(users["alice"])})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    make_profile(users["bob"], "Bob")   # another account isn't affected
    assert api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})[0] == 200
    clock["t"] += 61   # a minute later it works again
    assert api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})[0] == 200


def test_hourly_cap_applies_even_when_spread_out(api, users, make_profile, clock):
    make_profile(users["alice"], "Alice")
    for i in range(600):
        clock["t"] += 5   # 12 a minute: never hits the per-minute rule
        assert api.post("/api/like", user=users["alice"], json={"to_user": f"n{i}", "game": "cs2"})[0] == 404
    clock["t"] += 5
    status, d = api.post("/api/like", user=users["alice"], json={"to_user": "n", "game": "cs2"})
    assert status == 429 and "minutes" in d["detail"]


# R6-L01 — Retry-After is the wait until EVERY rule has room again
def test_retry_after_covers_every_saturated_rule(clock):
    rules = ((2, 10), (4, 100))
    for t in (0, 1, 50, 51):
        clock["t"] = 1000.0 + t
        main.check_rate("u:x", "test", rules)
    clock["t"] = 1052.0
    with pytest.raises(HTTPException) as e:
        main.check_rate("u:x", "test", rules)
    wait = int(e.value.headers["Retry-After"])
    assert wait == 100 - 52   # the 100 s rule frees its first slot at t=100
    clock["t"] = 1052.0 + wait
    main.check_rate("u:x", "test", rules)   # and then it really works


def test_concurrent_requests_never_exceed_the_limit(clock):
    ok, refused = [], []

    def hit():
        try:
            main.check_rate("u:y", "test", ((60, 60),))
            ok.append(1)
        except HTTPException:
            refused.append(1)
    threads = [threading.Thread(target=hit) for _ in range(300)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(ok) == 60 and len(refused) == 240


def test_idle_keys_are_forgotten(clock):
    for i in range(500):
        main.check_rate(f"ip:10.0.0.{i}", "test", ((5, 60),))
    assert len(main._hits) == 500
    clock["t"] += 61 + main.SWEEP_EVERY
    main.check_rate("ip:1.1.1.1", "test", ((5, 60),))
    assert len(main._hits) == 1


# R6-M03 — every social read shares the poll's budget; other expensive reads are limited too
def test_social_reads_share_one_budget(api, users, make_profile, clock):
    make_profile(users["alice"], "Alice")
    for _ in range(60):
        assert api.get("/api/poll?game=cs2", user=users["alice"])[0] == 200
    for path in ("/api/poll", "/api/incoming-likes", "/api/my-squad-details", "/api/pending-likes"):
        assert api.get(path + "?game=cs2", user=users["alice"])[0] == 429, path


def test_private_reads_and_public_pages_are_limited(api, users, make_profile, clock):
    make_profile(users["alice"], "Alice")
    for _ in range(60):
        api.get("/api/account", user=users["alice"])
    assert api.get("/api/account", user=users["alice"])[0] == 429
    ip = {"CF-Connecting-IP": "203.0.113.7"}
    for _ in range(300):
        assert api.client.get("/u/alice", headers=ip).status_code == 200
    assert api.client.get("/u/alice", headers=ip).status_code == 429
    assert api.get("/api/public-profile?username=alice", headers=ip)[0] == 429   # same public budget
    assert api.client.get("/u/alice", headers={"CF-Connecting-IP": "198.51.100.9"}).status_code == 200


def test_plain_health_is_never_limited_but_deep_is(api, clock):
    for _ in range(200):
        assert api.client.get("/health").status_code == 200
    for _ in range(30):
        assert api.client.get("/health?deep=1").status_code == 200
    assert api.client.get("/health?deep=1").status_code == 429


def test_client_ip_trusts_cloudflare_then_the_last_forwarded_entry():
    from starlette.requests import Request

    def req(headers):
        return Request({"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
                        "client": ("10.1.1.1", 1234)})
    assert main.client_ip(req({"CF-Connecting-IP": "203.0.113.7", "X-Forwarded-For": "1.2.3.4"})) == "203.0.113.7"
    assert main.client_ip(req({"X-Forwarded-For": "6.6.6.6, 198.51.100.9"})) == "198.51.100.9"   # client can't pick
    assert main.client_ip(req({"CF-Connecting-IP": "not-an-ip"})) == "10.1.1.1"
    assert main.client_ip(req({})) == "10.1.1.1"


def test_unauthenticated_calls_are_401_not_counted(api):
    for _ in range(100):
        assert api.post("/api/like", json={"to_user": "x", "game": "cs2"})[0] == 401
    assert all(not k.startswith("like:") for k in main._hits)
