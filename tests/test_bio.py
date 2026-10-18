"""Pre-launch #2: accounts.bio is the one source of truth; the match list shows the returned players' bios."""
import main


def test_bio_lives_in_accounts_and_every_reader_agrees(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice")
    assert api.put("/api/account", user=a, json={"bio": "Chill CS2 player, evenings"})[0] == 200
    assert next(r for r in db.tables["accounts"] if r["user_id"] == a)["bio"] == "Chill CS2 player, evenings"
    assert "bio" not in (db.users[a].app_metadata.get("playmate") or {})          # not written to Auth any more
    assert api.get("/api/account", user=a)[1]["bio"] == "Chill CS2 player, evenings"
    assert api.get("/api/public-profile?username=alice")[1]["bio"] == "Chill CS2 player, evenings"
    api.put("/api/account", user=a, json={"bio": ""})                             # cleared on purpose
    assert next(r for r in db.tables["accounts"] if r["user_id"] == a)["bio"] == ""
    assert api.get("/api/public-profile?username=alice")[1]["bio"] == ""


def test_an_old_auth_bio_never_comes_back(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice")
    db.users[a].app_metadata["playmate"] = {"bio": "OLD BIO in Auth"}             # e.g. from before migration 008
    api.put("/api/account", user=a, json={"bio": ""})
    api.put("/api/account", user=a, json={"banner": "banner-3"})                  # another field rewrites metadata
    assert api.get("/api/account", user=a)[1]["bio"] == ""
    assert api.get("/api/public-profile?username=alice")[1]["bio"] == ""


def test_pre_claim_bio_is_carried_into_the_new_account(api, users, db):
    a = users["alice"]
    db.users[a].app_metadata["playmate"] = {"bio": "  legacy bio  "}
    from conftest import BASE_PROFILE
    api.post("/api/profile", user=a, json={**BASE_PROFILE, "username": "Alice", "game": "cs2", "platform": "PC",
                                            "fields": {"mode": "Premier", "rank": "Silver"}})
    assert next(r for r in db.tables["accounts"] if r["user_id"] == a)["bio"] == "legacy bio"


def test_match_cards_carry_bios_in_one_query(api, users, make_profile, db, monkeypatch):
    a, b, c = users["alice"], users["bob"], users["carol"]
    for uid, name in ((a, "Alice"), (b, "Bob"), (c, "Carol")):
        make_profile(uid, name, in_game_username=f"{name}IGN", discord_username=f"{name}_dc")
    api.put("/api/account", user=b, json={"bio": "Bob loves Premier & clutches 🎯"})
    reads = []
    real = db.table
    monkeypatch.setattr(db, "table", lambda name: (reads.append(name), real(name))[1])
    _, d = api.post("/api/match", user=a, json={"game": "cs2"})
    bios = {m["username"]: m["profile"].get("bio") for m in d["matches"]}
    assert bios == {"bob": "Bob loves Premier & clutches 🎯", "carol": ""}
    assert reads.count("accounts") == 1                                            # one batch, no per-player lookups
    flat = str(d)
    assert "BobIGN" not in flat and "Bob_dc" not in flat and "_uid" not in flat and b not in flat


def test_bio_validation(api, users, make_profile):
    a = users["alice"]
    make_profile(a, "Alice")
    assert api.put("/api/account", user=a, json={"bio": "x" * 281})[0] == 422
    assert api.put("/api/account", user=a, json={"bio": "<b>hi</b>"})[0] == 422
    assert api.put("/api/account", user=a, json={"bio": "🎮" * 280})[0] == 200     # 280 characters (code points)
