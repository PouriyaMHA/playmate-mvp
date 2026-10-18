"""Regression tests for review 11 (docs/reviews/2026-10-18-review-11.md) — backend parts."""
import main


def _pool(api, user, **opts):
    status, d = api.post("/api/match", user=user, json={"game": "cs2", **opts})
    assert status == 200, d
    return d["pool"], [m["username"] for m in d["matches"]]


# F9: "skipped" is counted after the filters, so "see the ones you skipped" really shows someone
def test_skipped_count_respects_the_filters(api, users, make_profile):
    make_profile(users["alice"], "Alice", languages="fa")
    make_profile(users["bob"], "Bob", languages="en")
    p, names = _pool(api, users["alice"], exclude=["bob"], same_language_only=True)
    # review 12 N1: hidden by BOTH -> its own bucket, so neither single action promises him
    assert names == [] and p["skipped"] == 0 and p["filtered"] == 0 and p["skipped_filtered"] == 1
    p, names = _pool(api, users["alice"], exclude=["bob"])
    assert names == [] and p["skipped"] == 1
    assert p["complete"] is True


def test_pool_says_when_the_scan_was_bounded(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    db.tables["profiles"] += [{"id": f"x{i}", "user_id": f"u{i}", "username": f"p{i}", "game": "cs2",
                               "region": "middle-east", "platform": "PC", "game_meta": {}} for i in range(500)]
    p, _ = _pool(api, users["alice"])
    assert p["complete"] is False


# F4: a bio write that hits no row (account deleted meanwhile) is not a success; vanished accounts aren't cards
def test_bio_write_after_deletion_is_not_a_success(api, users, make_profile, db, monkeypatch):
    a = users["alice"]
    make_profile(a, "Alice")
    db.tables["accounts"] = [r for r in db.tables["accounts"] if r["user_id"] != a]   # deleted after the check...
    monkeypatch.setattr(main, "account_row", lambda uid: {"username": "alice"})        # ...which still saw it
    status, d = api.put("/api/account", user=a, json={"bio": "new bio"})
    assert status == 401 and "no longer exists" in d["detail"]


def test_players_whose_account_vanished_are_not_returned(api, users, make_profile, db):
    for uid, name in ((users["alice"], "Alice"), (users["bob"], "Bob"), (users["carol"], "Carol")):
        make_profile(uid, name)
    db.tables["accounts"] = [r for r in db.tables["accounts"] if r["user_id"] != users["carol"]]
    _, names = _pool(api, users["alice"])
    assert names == ["bob"]


# F10 + distinct titles
def test_privacy_lists_what_is_public_and_the_browser_items(api):
    html = api.client.get("/privacy").text
    assert "last active" in html and "list of your squadmates" in html and "Session storage" in html
    assert "<title>Privacy policy — PlayMate</title>" in html
    assert "<title>Terms of use — PlayMate</title>" in api.client.get("/terms").text
