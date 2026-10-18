"""Steam profile link: offered for Steam games on PC, normalized, mutual-only (like IGN / Discord)."""
import pytest
from fastapi import HTTPException

import main
from games import offers_steam


@pytest.mark.parametrize("raw, stored", [
    ("https://steamcommunity.com/id/gaben/", "id/gaben"),
    ("steamcommunity.com/id/Pro_Player-1", "id/Pro_Player-1"),
    ("http://www.steamcommunity.com/profiles/76561197960287930", "profiles/76561197960287930"),
    ("https://steamcommunity.com/profiles/76561197960287930/?xml=1", "profiles/76561197960287930"),
    ("76561197960287930", "profiles/76561197960287930"),
    ("22202", "profiles/76561197960287930"),            # friend code → SteamID64
    ("gaben", "id/gaben"),                              # custom URL name
    # R9-M01: the account id's whole 32-bit range, not a decimal prefix
    ("1", "profiles/76561197960265729"),
    ("2039734271", "profiles/76561199999999999"),
    ("2039734272", "profiles/76561200000000000"),       # crosses the 7656119… → 7656120… prefix
    ("4294967295", "profiles/76561202255233023"),       # largest friend code
    ("76561202255233023", "profiles/76561202255233023"),
    ("https://steamcommunity.com/profiles/76561200000000000#x", "profiles/76561200000000000"),
    ("steamcommunity.com/id/123", "id/123"),            # numeric custom URL only inside a link
    ("  ", None), ("", None), (None, None),
])
def test_steam_input_is_normalized(raw, stored):
    assert main.clean_steam_profile(raw) == stored


@pytest.mark.parametrize("raw", [
    "https://evil.example/id/gaben", "https://steamcommunity.com.evil.io/id/x", "javascript:alert(1)",
    "steamcommunity.com/id/<script>", "a", "x" * 40, "https://steamcommunity.com/profiles/123",
    "https://steamcommunity.com/groups/abc", "id/gaben?x=1", "12345678901234",
    # R9-M01: outside the individual-account range
    "0", "76561197960265728", "76561190000000000", "76561202255233024", "https://steamcommunity.com/profiles/22202",
    # R9-L01: only ASCII digits (no superscripts / other scripts), never a 500
    "²", "7656119١١١١١١١١١١", "٢٢٢٠٢",
    "https://steamcommunity.com/profiles/7656119١١١١١١١١١١",
    "gabén",
])
def test_bad_steam_input_is_refused(raw):
    with pytest.raises(HTTPException) as e:
        main.clean_steam_profile(raw)
    assert e.value.status_code == 422


def test_offered_only_for_steam_games_on_pc():
    assert offers_steam("cs2", "PC") and offers_steam("gta", "PC (Enhanced)") and offers_steam("battlefield", "PC")
    assert not offers_steam("gta", "PlayStation") and not offers_steam("lol", "PC")
    assert not offers_steam("pubg-mobile", "Android") and not offers_steam("fortnite", "PC")
    assert main.game_meta("cs2")["steam"] is True and main.game_meta("lol")["steam"] is False


def test_steam_profile_is_mutual_only(api, users, make_profile):
    a, b, c = users["alice"], users["bob"], users["carol"]
    make_profile(a, "Alice")
    make_profile(b, "Bob", steam_profile="https://steamcommunity.com/id/bobsteam")
    make_profile(c, "Carol")
    assert api.get("/api/my-profile?game=cs2", user=b)[1]["steam_profile"] == "id/bobsteam"
    api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert "bobsteam" not in str(d)                                   # incoming: not yet
    assert "bobsteam" not in str(api.post("/api/match", user=a, json={"game": "cs2"})[1])
    assert "bobsteam" not in str(api.get("/api/public-profile?username=bob")[1])
    assert "bobsteam" not in str(api.get("/profile-squad?username=bob&game=cs2")[1])
    assert "bobsteam" not in str(api.get("/api/relationship?username=bob", user=a)[1])
    api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert d["squadmates"][0]["steam_profile"] == "id/bobsteam"       # mutual: yes
    assert "bobsteam" not in str(api.get("/api/poll?game=cs2", user=c)[1])


def test_steam_profile_is_dropped_where_it_is_not_offered(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice", "gta", platform="PlayStation", steam_profile="gaben")
    make_profile(a, "Alice", "lol", steam_profile="gaben")
    assert all(r.get("steam_profile") is None for r in db.tables["profiles"])
    status, d = api.post("/api/profile", user=a, json={
        "username": "Alice", "game": "cs2", "platform": "PC", "region": "middle-east", "country": "Iran",
        "mic": "voice", "languages": "fa", "fields": {"mode": "Premier", "rank": "Silver"},
        "steam_profile": "https://evil.example/id/x"})
    assert status == 422 and "Steam profile" in d["detail"]



def test_unicode_digits_are_a_422_not_a_500(api, users):
    from conftest import BASE_PROFILE
    status, d = api.post("/api/profile", user=users["alice"], json={
        **BASE_PROFILE, "username": "Alice", "game": "cs2", "platform": "PC",
        "fields": {"mode": "Premier", "rank": "Silver"}, "steam_profile": "²"})
    assert status == 422 and "Steam profile" in d["detail"]
