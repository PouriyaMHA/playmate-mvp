"""Regression tests for the fourth Codex review (docs/reviews/2026-10-18-review-4.md)."""


# R4-M01 — a public squad list never shows the logged-in viewer a player blocked either way (any game)
def test_profile_squad_hides_players_blocked_with_the_viewer(api, users, make_profile):
    a, b, c = users["alice"], users["bob"], users["carol"]
    for uid, name in ((a, "Alice"), (b, "Bob"), (c, "Carol")):
        make_profile(uid, name)
    make_profile(b, "Bob", "gta")
    make_profile(a, "Alice", "gta")
    for x, y in ((a, c), (b, c), (a, b)):   # a triangle of mutual likes in cs2
        for frm, to in ((x, y), (y, x)):
            name = {a: "alice", b: "bob", c: "carol"}[to]
            api.post("/api/like", user=frm, json={"to_user": name, "game": "cs2"})
    api.post("/api/block", user=a, json={"to_user": "bob", "game": "gta"})   # blocked in another game
    squad = lambda **kw: api.get("/profile-squad?username=carol&game=cs2", **kw)
    assert {m["username"] for m in squad()[1]["squadmates"]} == {"alice", "bob"}            # guests: unchanged
    assert {m["username"] for m in squad(user=a)[1]["squadmates"]} == {"alice"}              # alice: no bob
    assert {m["username"] for m in squad(user=b)[1]["squadmates"]} == {"bob"}                # bob: no alice
    assert api.get("/profile-squad?username=bob&game=cs2", user=a)[0] == 404                # bob's own squad
    assert "in_game_username" not in str(squad()[1])
