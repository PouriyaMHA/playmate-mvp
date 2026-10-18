"""API behaviour against the fake database: auth, profiles, matching, likes/squad, safety, account."""
import pytest

from conftest import make_token


# ---------------------------------------------------------------- auth (JWT)
@pytest.mark.parametrize("claims", [
    {"aud": None}, {"aud": "anon"}, {"exp": None}, {"exp": 1},
])
def test_bad_tokens_are_rejected(api, users, claims):
    assert api.get("/api/my-games", token=make_token(users["alice"], **claims))[0] == 401


def test_non_uuid_subject_rejected(api):
    assert api.get("/api/my-games", token=make_token("not-a-uuid"))[0] == 401


def test_private_endpoints_need_login(api):
    for path in ("/api/my-games", "/api/account", "/api/blocks", "/api/my-profile", "/api/incoming-likes"):
        assert api.get(path)[0] == 401, path


# ---------------------------------------------------------------- profiles
def test_profile_validation(api, users, make_profile):
    a = users["alice"]
    status, d = api.post("/api/profile", user=a, json={"username": "Al", "game": "cs2"})
    assert status == 422
    base = {"username": "Alice", "region": "middle-east", "country": "Iran", "mic": "voice", "languages": "fa"}
    status, d = api.post("/api/profile", user=a, json={**base, "game": "battlefield", "fields": {"favorite_mode": "Conquest"}})
    assert status == 422 and "Platform" in d["detail"]
    status, d = api.post("/api/profile", user=a, json={**base, "country": "Japan", "game": "cs2", "fields": {"mode": "Premier", "rank": "Silver"}})
    assert status == 422 and "Country" in d["detail"]
    data = make_profile(a, "Alice")   # cs2 is PC-only: platform filled in
    assert data["data"]["platform"] == "PC"


def test_username_locked_across_games(api, users, make_profile):
    make_profile(users["alice"], "Alice", "cs2")
    make_profile(users["alice"], "SomethingElse", "battlefield")
    _, d = api.get("/api/my-games", user=users["alice"])
    assert d["username"] == "alice" and sorted(d["games"]) == ["battlefield", "cs2"]


def test_username_taken(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    status, d = api.post("/api/profile", user=users["bob"], json={
        "username": "alice", "game": "cs2", "region": "middle-east", "country": "Iran", "mic": "voice",
        "languages": "fa", "fields": {"mode": "Premier", "rank": "Silver"}})
    assert status == 409


def test_city_from_other_country_dropped_and_country_derived(api, users, make_profile, db):
    make_profile(users["alice"], "Alice", country="Turkey", city="Tehran")
    _, d = api.get("/api/my-profile?game=cs2", user=users["alice"])
    assert d["country"] == "Turkey" and d["city"] is None
    # an old row without game_meta.country derives it from the city
    db.tables["profiles"][0]["game_meta"].pop("country")
    db.tables["profiles"][0]["region"], db.tables["profiles"][0]["city"] = "na-west", "Vancouver"
    _, d = api.get("/api/my-profile?game=cs2", user=users["alice"])
    assert d["country"] == "Canada"


# ---------------------------------------------------------------- matching
def test_match_hides_private_fields_and_respects_crossplay(api, users, make_profile):
    make_profile(users["alice"], "Alice", "gta", platform="PC (Enhanced)", in_game_username="AliceGTA")
    make_profile(users["bob"], "Bob", "gta", platform="PC (Legacy)", discord_username="bob#1")
    make_profile(users["carol"], "Carol", "gta", platform="PC (Enhanced)", in_game_username="CarolGTA", discord_username="carol#1")
    _, d = api.post("/api/match", user=users["alice"], json={"game": "gta"})
    names = [m["username"] for m in d["matches"]]
    assert names == ["carol"]
    assert "CarolGTA" not in str(d) and "carol#1" not in str(d)


def test_match_exclude_has_more_and_likes_you(api, users, make_profile):
    for name in ("alice", "bob", "carol"):
        make_profile(users[name], name.title())
    api.post("/api/like", user=users["carol"], json={"to_user": "alice", "game": "cs2"})
    _, d = api.post("/api/match", user=users["alice"], json={"game": "cs2"})
    assert d["matches"][0]["username"] == "carol" and d["matches"][0]["likes_you"] is True
    assert d["has_more"] is False
    _, d = api.post("/api/match", user=users["alice"], json={"game": "cs2", "exclude": ["CAROL"]})
    assert [m["username"] for m in d["matches"]] == ["bob"]


# ---------------------------------------------------------------- likes, squad, incoming
def test_like_flow(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice", in_game_username="AliceCS")
    make_profile(b, "Bob", in_game_username="BobCS", discord_username="bob#1")
    _, d = api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})
    assert d["status"] == "liked" and d["mutual"] is False
    _, inc = api.get("/api/incoming-likes?game=cs2", user=a)
    assert [p["username"] for p in inc["incoming"]] == ["bob"] and "BobCS" not in str(inc)
    _, pend = api.get("/api/pending-likes?game=cs2", user=b)
    assert [p["username"] for p in pend["pending"]] == ["alice"]
    _, d = api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})
    assert d["mutual"] is True
    _, d = api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})
    assert d["status"] == "already_exists"
    _, sq = api.get("/api/my-squad-details?game=cs2", user=a)
    assert sq["squadmates"][0]["in_game_username"] == "BobCS" and sq["squadmates"][0]["discord_username"] == "bob#1"
    assert api.get("/api/incoming-likes?game=cs2", user=a)[1]["incoming"] == []


def test_unmatch_removes_both_likes(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    assert api.delete("/api/like?to_user=bob&game=cs2", user=users["alice"])[0] == 200
    assert db.tables["likes"] == []
    assert api.delete("/api/like?to_user=nobody&game=cs2", user=users["alice"])[0] == 404


def test_cannot_like_yourself_or_unknown(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    assert api.post("/api/like", user=users["alice"], json={"to_user": "alice", "game": "cs2"})[0] == 400
    assert api.post("/api/like", user=users["alice"], json={"to_user": "ghost", "game": "cs2"})[0] == 404


# ---------------------------------------------------------------- block / report / unblock
def test_block_hides_everywhere(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    for g in ("cs2", "battlefield"):
        make_profile(a, "Alice", g)
        make_profile(b, "Bob", g)
    api.post("/api/like", user=b, json={"to_user": "alice", "game": "battlefield"})
    api.post("/api/block", user=a, json={"to_user": "bob", "game": "cs2"})
    for g in ("cs2", "battlefield"):
        assert api.post("/api/match", user=a, json={"game": g})[1]["matches"] == []
        assert api.post("/api/match", user=b, json={"game": g})[1]["matches"] == []
    assert api.get("/api/incoming-likes?game=battlefield", user=a)[1]["incoming"] == []
    assert api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})[0] == 403
    assert api.get("/api/public-profile?username=bob", user=a)[0] == 404
    assert api.get("/api/public-profile?username=alice", user=b)[0] == 404
    assert api.get("/api/public-profile?username=bob")[0] == 200   # logged-out visitors


def test_report_is_kept_and_blocks_unblock(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2", "report": True, "reason": "Cheating"})
    _, d = api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    assert d["reported"] is True and db.tables["blocks"][0]["reason"] == "Cheating"
    _, d = api.get("/api/blocks", user=users["alice"])
    assert d["blocked"][0]["username"] == "bob" and d["blocked"][0]["reported"] is True
    assert api.delete("/api/block?to_user=bob", user=users["alice"])[0] == 409


def test_unblock(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    assert api.delete("/api/block?to_user=bob", user=users["alice"])[0] == 200
    assert api.get("/api/blocks", user=users["alice"])[1]["blocked"] == []
    assert [m["username"] for m in api.post("/api/match", user=users["alice"], json={"game": "cs2"})[1]["matches"]] == ["bob"]


# ---------------------------------------------------------------- account
def test_account_avatar_is_copied_to_profiles(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    assert api.put("/api/account", user=users["bob"], json={"avatar": "avatar-19"})[0] == 200
    assert api.put("/api/account", user=users["bob"], json={"avatar": "avatar-99"})[0] == 422
    _, d = api.post("/api/match", user=users["alice"], json={"game": "cs2"})
    assert d["matches"][0]["profile"]["avatar"] == "avatar-19"


def test_auth_outage_keeps_avatar(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    api.put("/api/account", user=users["alice"], json={"avatar": "avatar-14"})
    db.auth.admin.fail = True
    assert api.get("/api/account", user=users["alice"])[0] == 503
    make_profile(users["alice"], "Alice")   # saving during the outage must not wipe the copied avatar
    db.auth.admin.fail = False
    assert db.tables["profiles"][0]["game_meta"]["avatar"] == "avatar-14"


def test_delete_account(api, users, make_profile, db):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob")
    api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})
    api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "cs2"})
    assert api.call("DELETE", "/api/account", user=a, json={"confirm": "nope"})[0] == 422
    assert api.call("DELETE", "/api/account", user=a, json={"confirm": "DELETE"})[0] == 200
    assert a not in db.users
    assert all(r["user_id"] != a for r in db.tables["profiles"])
    assert db.tables["likes"] == [] and db.tables["blocks"] == []


# ---------------------------------------------------------------- pages and headers
def test_security_headers(api):
    status, _ = api.get("/")
    r = api.client.get("/")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    r = api.client.get("/api/games")
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/", "/app", "/settings", "/terms", "/privacy"])
def test_pages_load(api, path):
    assert api.client.get(path).status_code == 200


def test_unknown_page_is_404(api):
    assert api.client.get("/nothing-here").status_code == 404


# ---------------------------------------------------------------- poll (the 15-second refresh)
def test_poll_returns_squad_pending_incoming_in_one_call(api, users, make_profile, db):
    a, b, c = users["alice"], users["bob"], users["carol"]
    make_profile(a, "Alice")
    make_profile(b, "Bob", in_game_username="BobCS")
    make_profile(c, "Carol", in_game_username="CarolCS")
    api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})     # mutual
    api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})
    api.post("/api/like", user=c, json={"to_user": "alice", "game": "cs2"})   # carol liked alice
    status, d = api.get("/api/poll?game=cs2&ping=1", user=a)
    assert status == 200
    assert [m["username"] for m in d["squadmates"]] == ["bob"] and d["squadmates"][0]["in_game_username"] == "BobCS"
    assert [p["username"] for p in d["incoming"]] == ["carol"] and "CarolCS" not in str(d["incoming"])
    assert d["pending"] == []
    alice_row = next(r for r in db.tables["profiles"] if r["user_id"] == a)
    assert alice_row.get("last_active")   # ping=1 marked her active
    _, d = api.get("/api/poll?game=cs2", user=c)
    assert [p["username"] for p in d["pending"]] == ["alice"]
    assert api.get("/api/poll?game=battlefield", user=a)[0] == 404   # no profile in that game


def test_poll_without_ping_does_not_touch_last_active(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    api.get("/api/poll?game=cs2", user=users["alice"])
    assert not db.tables["profiles"][0].get("last_active")


def test_games_and_stats_counts(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    _, d = api.get("/api/games")
    assert {g["id"]: g["players"] for g in d["games"]}["cs2"] == 2
    _, s = api.get("/api/stats?game=cs2&region=middle-east")
    assert s["players"] == 2 and s["in_region"] == 2


def test_profile_page_has_player_title_and_404s_for_unknown(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    r = api.client.get("/u/alice")
    assert r.status_code == 200 and "<title>Alice on PlayMate</title>" in r.text and 'og:title' in r.text
    assert "Counter-Strike 2" in r.text
    assert api.client.get("/u/nobody_here").status_code == 404
    assert api.client.get("/profile").status_code == 200


# ---------------------------------------------------------------- usernames (accounts table)
def test_username_is_reserved_on_the_account(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    assert [(r["username"], r["display_username"]) for r in db.tables["accounts"]] == [("alice", "Alice")]
    # removing her only game keeps the name reserved...
    assert api.delete("/api/profile?game=cs2", user=users["alice"])[0] == 200
    status, d = api.post("/api/profile", user=users["bob"], json={
        "username": "ALICE", "game": "cs2", "region": "middle-east", "country": "Iran", "mic": "voice",
        "languages": "fa", "fields": {"mode": "Premier", "rank": "Silver"}})
    assert status == 409
    # ...and she gets it back automatically, whatever she types now
    make_profile(users["alice"], "SomethingElse", "battlefield")
    _, d = api.get("/api/my-games", user=users["alice"])
    assert d["username"] == "alice" and d["display_username"] == "Alice"
    assert api.get("/api/account", user=users["alice"])[1]["username"] == "alice"


def test_failed_validation_does_not_reserve_a_name(api, users, db):
    status, _ = api.post("/api/profile", user=users["alice"], json={"username": "Alice", "game": "cs2"})
    assert status == 422 and db.tables.get("accounts", []) == []


def test_old_player_without_account_row_gets_one(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    db.tables["accounts"] = []   # as if she signed up before the migration
    make_profile(users["alice"], "Alice")
    assert [r["username"] for r in db.tables["accounts"]] == ["alice"]


def test_delete_account_frees_the_name(api, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    api.call("DELETE", "/api/account", user=users["alice"], json={"confirm": "DELETE"})
    assert db.tables["accounts"] == []
    make_profile(users["bob"], "Alice")


def test_works_before_the_migration(api, users, make_profile, db, monkeypatch):
    """Without the accounts table the app falls back to profile usernames."""
    real_table = db.table

    def no_accounts(name):
        if name == "accounts":
            raise Exception('relation "public.accounts" does not exist')
        return real_table(name)
    monkeypatch.setattr(db, "table", no_accounts)
    make_profile(users["alice"], "Alice")
    _, d = api.get("/api/my-games", user=users["alice"])
    assert d["username"] == "alice"
    assert api.post("/api/profile", user=users["bob"], json={
        "username": "alice", "game": "cs2", "region": "middle-east", "country": "Iran", "mic": "voice",
        "languages": "fa", "fields": {"mode": "Premier", "rank": "Silver"}})[0] == 409
