"""Regression tests for the third Codex review (docs/reviews/2026-10-18-review-3.md)."""


# R3-H03 — likes, blocks and contact info come from ONE read: nothing written between reads can leak
def test_poll_contact_comes_from_the_same_read_as_the_block(api, users, make_profile, db, monkeypatch):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobOld")
    api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    real_rpc = db.rpc

    def block_then_change_contact_right_after_the_read(name, params):
        res = real_rpc(name, params).execute()   # the poll's snapshot is taken here...
        db.tables.setdefault("blocks", []).append(   # ...then bob blocks alice and saves a new IGN
            {"id": "b1", "blocker_id": users["bob"], "blocked_id": users["alice"], "game": "cs2", "reported": False})
        next(p for p in db.tables["profiles"] if p["user_id"] == users["bob"])["in_game_username"] = "NEW_AFTER_BLOCK"
        return type("R", (), {"execute": lambda self: res})()
    monkeypatch.setattr(db, "rpc", block_then_change_contact_right_after_the_read)
    _, d = api.get("/api/poll?game=cs2", user=users["alice"])
    assert "NEW_AFTER_BLOCK" not in str(d)
    monkeypatch.setattr(db, "rpc", real_rpc)
    _, d = api.get("/api/poll?game=cs2", user=users["alice"])
    assert d["squadmates"] == [] and "NEW_AFTER_BLOCK" not in str(d)


def test_blocked_players_profiles_never_leave_the_db(db, users, make_profile, api):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobCS")
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    snap = db.rpc("social_snapshot", {"viewer": users["alice"], "g": "cs2"}).execute().data
    assert snap["profiles"] == [] and snap["blocked"] == [users["bob"]]


# R3-M03 — more than 1000 like rows: every mutual is still a mutual
def test_social_lists_are_not_cut_at_1000_rows(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    a = users["alice"]
    likes = db.tables.setdefault("likes", [])
    profiles = db.tables["profiles"]
    for i in range(600):
        u = f"u{i}"
        profiles.append({"id": f"p{i}", "user_id": u, "username": f"p{i}", "display_username": f"p{i}", "game": "cs2",
                         "region": "middle-east", "game_meta": {}})
        likes.append({"id": f"a{i}", "from_user_id": a, "to_user_id": u, "game": "cs2", "created_at": "2026-10-18"})
    for i in range(600):
        likes.append({"id": f"b{i}", "from_user_id": f"u{i}", "to_user_id": a, "game": "cs2", "created_at": "2026-10-18"})
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert len(d["squadmates"]) == 600 and d["pending"] == []
