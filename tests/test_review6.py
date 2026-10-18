"""Regression tests for the sixth Codex review (docs/reviews/2026-10-18-review-6.md)."""
import main


# R6-M01 — a save still on its way while the account is deleted can't leave an orphan profile / like / block
def test_late_writes_after_account_deletion_are_refused(api, users, make_profile, db, monkeypatch):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob")
    real_upsert_table = db.table
    state = {"paused": False}

    def delete_account_right_before_the_upsert(name):
        q = real_upsert_table(name)
        if name == "profiles" and not state["paused"]:
            real_upsert = q.upsert

            def upsert(*args, **kw):
                state["paused"] = True
                assert api.delete("/api/account", user=a, json={"confirm": "DELETE"})[0] == 200
                return real_upsert(*args, **kw)
            q.upsert = upsert
        return q
    monkeypatch.setattr(db, "table", delete_account_right_before_the_upsert)
    status, d = api.post("/api/profile", user=a, json={
        "username": "Alice", "game": "cs2", "platform": "PC", "region": "middle-east", "country": "Iran",
        "mic": "voice", "languages": "fa", "fields": {"mode": "Premier", "rank": "Silver"}})
    monkeypatch.setattr(db, "table", real_upsert_table)
    assert status == 401 and "no longer exists" in d["detail"]
    assert [r for r in db.tables["profiles"] if r["user_id"] == a] == []
    assert api.get("/api/public-profile?username=alice")[0] == 404
    # a stale token of the deleted account can't like or block either
    assert api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})[0] in (401, 404)
    assert api.post("/api/block", user=a, json={"to_user": "bob", "game": "cs2"})[0] == 401
    assert db.tables.get("likes", []) == [] and db.tables.get("blocks", []) == []


def test_deleting_the_auth_user_cascades(api, users, make_profile, db):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob")
    api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "cs2"})
    db.auth.admin.delete_user(a)
    assert all(a not in (str(r.get("user_id")), str(r.get("from_user_id")), str(r.get("blocked_id")))
               for t in ("profiles", "likes", "blocks", "accounts") for r in db.tables.get(t, []))


# R6-M02 — accounts.avatar is the source of truth; every profile copy follows it
def test_profiles_always_end_with_the_account_avatar(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice")
    for av in ("avatar-3", "avatar-5", ""):
        api.put("/api/account", user=a, json={"avatar": av})
        acc = next(r for r in db.tables["accounts"] if r["user_id"] == a)
        assert (acc.get("avatar") or "") == av
        assert {(r["game_meta"].get("avatar") or "") for r in db.tables["profiles"]} == {av}
        assert api.get("/api/account", user=a)[1]["avatar"] == av
        assert api.get("/api/public-profile?username=alice")[1]["avatar"] == av
    make_profile(a, "Alice", "gta")   # a new game profile gets the account avatar too
    api.put("/api/account", user=a, json={"avatar": "avatar-7"})
    make_profile(a, "Alice", "lol")
    assert {r["game_meta"].get("avatar") for r in db.tables["profiles"]} == {"avatar-7"}


def test_avatar_needs_a_claimed_account_first(api, users, make_profile, db):
    """R7-M01: no accounts row = nothing to serialize avatar changes on, so they wait for the first profile."""
    a = users["alice"]
    status, d = api.put("/api/account", user=a, json={"avatar": "avatar-9"})
    assert status == 409 and "first game profile" in d["detail"]
    assert api.put("/api/account", user=a, json={"bio": "hi"})[0] == 200   # other account fields are fine
    make_profile(a, "Alice")
    assert api.put("/api/account", user=a, json={"avatar": "avatar-9"})[0] == 200
    assert db.tables["profiles"][0]["game_meta"]["avatar"] == "avatar-9"
