"""Pure rules: crossplay/hard filters, scoring, field cleaning, locations."""
import main
from games import GAMES, can_play_together, clean_fields
from locations import REGIONS, country_of_city, get_country


def test_crossplay_groups():
    assert can_play_together("gta", "PC (Enhanced)", "PC (Enhanced)", {}, {})
    assert not can_play_together("gta", "PC (Enhanced)", "PC (Legacy)", {}, {})
    assert not can_play_together("gta", "PlayStation", "Xbox", {}, {})
    assert can_play_together("fc", "PlayStation", "PC", {}, {})
    assert not can_play_together("fc", "PC", "Switch", {}, {})
    assert can_play_together("battlefield", "PC", "PlayStation", {}, {})


def test_unknown_values_never_block():
    assert can_play_together("gta", None, "Xbox", {}, {})
    assert can_play_together("minecraft", "PC", "PC", {"edition": "Java"}, {})


def test_must_match_fields():
    assert not can_play_together("minecraft", "PC", "PC", {"edition": "Java"}, {"edition": "Bedrock"})
    assert can_play_together("minecraft", "PC", "Xbox", {"edition": "Bedrock"}, {"edition": "Bedrock"})
    assert not can_play_together("lol", "PC", "PC", {"server": "EUW"}, {"server": "NA"})


def _p(game, **fields):
    return {"game": game, "region": "eu-west", "game_meta": {"fields": fields}}


def test_roles_score_when_different():
    me = _p("lol", server="EUW", role="Mid", rank="Gold")
    same, _ = main.score_pair(me, _p("lol", server="EUW", role="Mid", rank="Gold"), "lol")
    other, reasons = main.score_pair(me, _p("lol", server="EUW", role="Jungle", rank="Gold"), "lol")
    fill, _ = main.score_pair(me, _p("lol", server="EUW", role="Fill", rank="Gold"), "lol")
    assert other > same and fill == other
    assert any("Complementary main role" in r for r in reasons)


def test_score_capped_at_100():
    me = {"game": "battlefield", "region": "na-west", "city": "Vancouver", "mic": "voice", "platform": "PC",
          "languages": "en,fa", "game_meta": {"country": "Canada", "fields": {"favorite_mode": "Conquest", "class_type": "Assault"}}}
    other = {**me, "game_meta": {"country": "Canada", "fields": {"favorite_mode": "Conquest", "class_type": "Recon"}}}
    score, _ = main.score_pair(me, other, "battlefield")
    assert score == 100


def test_profile_fields_drop_removed_fields_and_keep_order():
    row = {"game": "cs2", "game_meta": {"fields": {"role": "AWPer", "rank": "Gold Nova", "mode": "Premier"}}}
    assert list(main.profile_fields(row)) == ["mode", "rank"]


def test_clean_fields():
    fields, missing = clean_fields("cs2", {"mode": "Premier", "rank": "nope", "hack": "x"})
    assert fields == {"mode": "Premier"} and missing == ["Rank"]


def test_every_game_is_consistent():
    for gid, g in GAMES.items():
        for grp in g.get("crossplay", []):
            assert set(grp) <= set(g["platforms"]), gid
        for f in g["fields"]:
            assert f["match"] in ("same", "diff") and f["options"], (gid, f["id"])


def test_locations():
    assert country_of_city("na-west", "Vancouver") == "Canada"
    assert country_of_city("eu-west", "London") == "United Kingdom"
    assert country_of_city("na-east", "London") == "Canada"
    assert get_country("middle-east", "Iran") and not get_country("asia", "Iran")
    for r in REGIONS:
        assert r["cities"] == [c for country in r["countries"] for c in country["cities"]]
