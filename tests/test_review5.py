"""Regression tests for the fifth Codex review (docs/reviews/2026-10-18-review-5.md)."""
import main


def _fields(api, user):
    return api.get("/api/my-profile?game=cs2", user=user)[1]


# R5-M01 — an avatar change never rolls back a profile edit saved at the same moment (and vice versa)
def test_avatar_change_keeps_a_concurrent_profile_edit(api, users, make_profile, db, monkeypatch):
    a = users["alice"]
    make_profile(a, "Alice", fields={"mode": "Premier", "rank": "Gold Nova"})
    real_rpc = db.rpc

    def edit_lands_first(name, params):
        if name == "set_account_avatar":   # a profile save commits right before the avatar change runs
            monkeypatch.setattr(db, "rpc", real_rpc)
            make_profile(a, "Alice", fields={"mode": "Competitive", "rank": "Silver"})
        return real_rpc(name, params)
    monkeypatch.setattr(db, "rpc", edit_lands_first)
    assert api.put("/api/account", user=a, json={"avatar": "avatar-3"})[0] == 200
    p = next(r for r in db.tables["profiles"] if r["user_id"] == a)
    assert p["game_meta"]["fields"] == {"mode": "Competitive", "rank": "Silver"}
    assert p["game_meta"]["avatar"] == "avatar-3"


def test_profile_save_racing_an_avatar_change_ends_with_the_new_avatar(api, users, make_profile, db, monkeypatch):
    a = users["alice"]
    make_profile(a, "Alice")
    real = main.current_avatar
    calls = {"n": 0}

    def avatar_changes_after_the_first_read(uid, row):
        calls["n"] += 1
        if calls["n"] == 1:
            old = real(uid, row)
            api.put("/api/account", user=a, json={"avatar": "avatar-5"})   # lands while the save is in flight
            return old
        return real(uid, row)
    monkeypatch.setattr(main, "current_avatar", avatar_changes_after_the_first_read)
    make_profile(a, "Alice", fields={"mode": "Wingman", "rank": "Silver"})
    p = next(r for r in db.tables["profiles"] if r["user_id"] == a)
    assert p["game_meta"]["avatar"] == "avatar-5" and p["game_meta"]["fields"]["mode"] == "Wingman"


def test_removing_the_avatar_clears_every_profile(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice")
    make_profile(a, "Alice", "gta")
    api.put("/api/account", user=a, json={"avatar": "avatar-2"})
    assert {r["game_meta"].get("avatar") for r in db.tables["profiles"]} == {"avatar-2"}
    api.put("/api/account", user=a, json={"avatar": ""})
    assert {r["game_meta"].get("avatar") for r in db.tables["profiles"]} == {None}
