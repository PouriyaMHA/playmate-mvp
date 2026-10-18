"""Pre-launch #6: the match response says why nobody is shown (counts about the asker's own view only)."""


def pool(api, user, **opts):
    status, d = api.post("/api/match", user=user, json={"game": "gta", **opts})
    assert status == 200, d
    return d["pool"], d["matches"]


def test_pool_explains_an_empty_list(api, users, make_profile, db):
    a, b, c = users["alice"], users["bob"], users["carol"]
    dave = db.auth.admin.create_user(email="dave@example.com")
    make_profile(a, "Alice", "gta", platform="PC (Enhanced)", languages="fa")
    make_profile(b, "Bob", "gta", platform="PlayStation", languages="fa")             # no crossplay
    make_profile(c, "Carol", "gta", platform="PC (Enhanced)", languages="en")         # other language
    make_profile(dave, "Dave", "gta", platform="PC (Enhanced)", languages="fa")
    p, m = pool(api, a)
    assert [x["username"] for x in sorted(m, key=lambda x: x["username"])] == ["carol", "dave"]
    assert p == {"incompatible": 1, "liked": 0, "skipped": 0, "filtered": 0, "complete": True}
    p, m = pool(api, a, same_language_only=True)
    assert [x["username"] for x in m] == ["dave"] and p["filtered"] == 1
    api.post("/api/like", user=a, json={"to_user": "dave", "game": "gta"})
    p, m = pool(api, a, same_language_only=True)
    assert m == [] and p == {"incompatible": 1, "liked": 1, "skipped": 0, "filtered": 1, "complete": True}
    p, m = pool(api, a, exclude=["carol"])
    assert m == [] and p["skipped"] == 1 and p["liked"] == 1


def test_blocked_players_are_not_counted_anywhere(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice", "gta", platform="PC (Enhanced)")
    make_profile(b, "Bob", "gta", platform="PlayStation")
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "gta"})
    p, m = pool(api, a)
    assert m == [] and p == {"incompatible": 0, "liked": 0, "skipped": 0, "filtered": 0, "complete": True}
    assert "bob" not in str(api.post("/api/match", user=a, json={"game": "gta"})[1])
