"""Regression tests for the second Codex review (docs/reviews/2026-10-18-review-2.md), one block per finding."""
import main


def _base(**over):
    return {"region": "middle-east", "country": "Iran", "mic": "voice", "languages": "fa", "game": "cs2",
            "fields": {"mode": "Premier", "rank": "Silver"}, **over}


# R2-H01 — "mutual" must come from ONE read of the likes, never from two different moments
def test_poll_reads_all_likes_in_one_query(api, users, make_profile, db, monkeypatch):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobCS")
    api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    real_table, real_rpc, reads, rpcs = db.table, db.rpc, [], []
    monkeypatch.setattr(db, "table", lambda name: (reads.append(name), real_table(name))[1])
    monkeypatch.setattr(db, "rpc", lambda name, params: (rpcs.append(name), real_rpc(name, params))[1])
    _, d = api.get("/api/poll?game=cs2", user=users["alice"])
    assert [m["username"] for m in d["squadmates"]] == ["bob"]
    assert rpcs == ["social_snapshot"] and "likes" not in reads and "blocks" not in reads   # R3: one statement


def test_one_way_likes_at_different_moments_are_not_mutual(api, users, make_profile, db):
    """The exact interleaving from the review: A->B exists, A takes it back, B likes A. Only one like exists."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobCS")
    api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.delete("/api/like?to_user=bob&game=cs2", user=users["alice"])
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    _, d = api.get("/api/poll?game=cs2", user=users["alice"])
    assert d["squadmates"] == [] and "BobCS" not in str(d)
    assert [p["username"] for p in d["incoming"]] == ["bob"]


# R2-H04 — accounts is the only source of names; two first saves of one user can't split the identity
def test_same_user_claim_race_uses_the_winning_name(api, users, db, monkeypatch):
    a = users["alice"]
    db.tables["accounts"] = [{"user_id": a, "username": "winner", "display_username": "Winner"}]
    real = main.account_row
    calls = {"n": 0}

    def first_call_misses(uid):   # the "loser" request checked before the winner's row existed
        calls["n"] += 1
        return None if calls["n"] == 1 else real(uid)
    monkeypatch.setattr(main, "account_row", first_call_misses)
    status, d = api.post("/api/profile", user=a, json=_base(username="loser", platform="PC"))
    assert status == 200 and d["data"]["username"] == "winner"
    assert {r["username"] for r in db.tables["profiles"]} == {"winner"}


def test_accounts_read_error_is_an_error_not_a_fallback(api, users, make_profile, db, monkeypatch):
    make_profile(users["alice"], "Alice")
    api.delete("/api/profile?game=cs2", user=users["alice"])   # name reserved, no games left
    real = db.table

    def accounts_down(name):
        if name == "accounts":
            raise RuntimeError("timeout")
        return real(name)
    monkeypatch.setattr(db, "table", accounts_down)
    from fastapi.testclient import TestClient
    from conftest import Api
    real_errors = Api(TestClient(main.app, raise_server_exceptions=False))   # see the HTTP status, like a browser
    status, _ = real_errors.post("/api/profile", user=users["bob"], json=_base(username="alice", platform="PC"))
    assert status >= 500   # never "200 with a name someone else owns"
    assert all(r["username"] != "alice" for r in db.tables["profiles"])


# R2-M03 — a plain block never clears a report; re-reporting without text keeps the reason
def test_report_survives_any_later_block_and_empty_rereport(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2", "report": True, "reason": "Cheating"})
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2", "report": True, "reason": ""})
    row = db.tables["blocks"][0]
    assert row["reported"] is True and row["reason"] == "Cheating"
    assert api.delete("/api/block?to_user=bob", user=users["alice"])[0] == 409
    assert len(db.tables["blocks"]) == 1


# R2-M04 — a blocked player who removed every game still shows up (and can be unblocked)
def test_blocked_player_without_games_is_listed(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.delete("/api/profile?game=cs2", user=users["bob"])
    _, d = api.get("/api/blocks", user=users["alice"])
    assert [b["username"] for b in d["blocked"]] == ["bob"]
    assert api.delete("/api/block?to_user=bob", user=users["alice"])[0] == 200


# R2-M06 — liking (incl. "Like back") respects the hard filters
def test_like_and_incoming_respect_crossplay(api, users, make_profile):
    make_profile(users["alice"], "Alice", "gta", platform="PC (Enhanced)")
    make_profile(users["bob"], "Bob", "gta", platform="PC (Enhanced)")
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "gta"})
    make_profile(users["bob"], "Bob", "gta", platform="PlayStation")   # bob moved to PlayStation
    assert api.get("/api/incoming-likes?game=gta", user=users["alice"])[1]["incoming"] == []
    status, d = api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "gta"})
    assert status == 409 and "can't play together" in d["detail"]


# R2-M07 — counts are exact beyond the API's 1000-row page
def test_player_counts_are_exact_past_1000_rows(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    db.tables["profiles"] += [{"id": f"x{i}", "user_id": f"u{i}", "username": f"p{i}", "game": "cs2", "game_meta": {}}
                              for i in range(1200)]
    main._cache.clear()
    _, d = api.get("/api/games")
    assert {g["id"]: g["players"] for g in d["games"]}["cs2"] == 1201


# R2-M08 — unknown regions don't create cache entries
def test_stats_ignores_unknown_regions(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    main._cache.clear()
    for i in range(30):
        api.get(f"/api/stats?game=cs2&region=junk{i}")
    assert len(main._cache) <= 3


# R2-L01 — one existence model for the profile page and its API
def test_profile_page_existence(api, users, make_profile):
    assert api.client.get("/u/x").status_code == 404            # not a valid name
    assert api.client.get("/u/nobody_here").status_code == 404
    make_profile(users["alice"], "Alice")
    api.delete("/api/profile?game=cs2", user=users["alice"])      # reserved name, zero games
    assert api.client.get("/u/alice").status_code == 200
    assert api.get("/api/public-profile?username=alice")[0] == 200
    assert api.get("/api/public-profile?username=alice")[1]["display_username"] == "Alice"
