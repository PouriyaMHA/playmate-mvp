"""Like / Like back from someone's public profile: GET /api/relationship (Codex review 7, product #6)."""


def states(api, viewer, name):
    status, d = api.get(f"/api/relationship?username={name}", user=viewer)
    assert status == 200, d
    return d["games"]


def test_relationship_states_per_game(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob", in_game_username="BobCS")
    make_profile(b, "Bob", "lol")                                  # alice doesn't play LoL
    make_profile(a, "Alice", "gta", platform="PlayStation")
    make_profile(b, "Bob", "gta", platform="PC (Enhanced)")        # no crossplay
    assert states(api, a, "bob") == {"cs2": "none", "lol": "no_profile", "gta": "incompatible"}
    api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})
    assert states(api, a, "bob")["cs2"] == "liked"
    assert states(api, b, "alice")["cs2"] == "likes_you"
    api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})
    assert states(api, a, "bob")["cs2"] == "mutual"
    status, d = api.get("/api/relationship?username=bob", user=a)
    assert "BobCS" not in str(d)                                   # never contact info here


def test_relationship_self_blocked_and_unknown(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob")
    assert api.get("/api/relationship?username=alice", user=a)[1]["self"] is True
    assert api.get("/api/relationship?username=nobody", user=a)[0] == 404
    assert api.get("/api/relationship?username=bob")[0] == 401     # login required
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "gta"})
    assert api.get("/api/relationship?username=bob", user=a)[0] == 404
    assert api.get("/api/relationship?username=alice", user=b)[0] == 404
