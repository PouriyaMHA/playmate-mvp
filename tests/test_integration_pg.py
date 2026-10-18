"""Integration tests against a REAL Postgres + PostgREST (CI job "integration" in .github/workflows/tests.yml):
tests/integration/schema.sql (copy of the production schema) + every db/migrations/*.sql, PostgREST with Supabase's
roles. Only Supabase Auth stays fake (tests/fakedb.FakeAdmin, mirrored into auth.users for the foreign keys).

Skipped unless PLAYMATE_PG_URL and PLAYMATE_PGRST_URL are set. Never point them at a real database: every test
starts by emptying the tables.
"""
import os
import threading
import time
from types import SimpleNamespace

import jwt
import pytest

import main
from conftest import TEST_SECRET, make_token
from fakedb import FakeAdmin

PG_URL = os.environ.get("PLAYMATE_PG_URL")
REST_URL = os.environ.get("PLAYMATE_PGRST_URL")
pytestmark = pytest.mark.skipif(not (PG_URL and REST_URL), reason="needs the CI Postgres + PostgREST")


def role_key(role):
    return jwt.encode({"role": role, "exp": int(time.time()) + 3600}, TEST_SECRET, algorithm="HS256")


def rest_client(token):
    from postgrest import SyncPostgrestClient
    return SyncPostgrestClient(REST_URL, headers={"apikey": token, "Authorization": f"Bearer {token}"})


def sql(query, params=None, fetch=False):
    import psycopg
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        cur = conn.execute(query, params)
        return cur.fetchall() if fetch else None


class PgAdmin(FakeAdmin):
    """Fake Auth (app_metadata in memory) that also keeps auth.users rows, so accounts' foreign key works."""

    def create_user(self, uid=None, email="", created_at=None):
        uid = super().create_user(uid, email, created_at)
        sql("insert into auth.users (id, email) values (%s, %s)", (uid, email))
        return uid

    def delete_user(self, uid):
        self._user(uid)
        del self.db.users[str(uid)]
        sql("delete from auth.users where id = %s", (str(uid),))   # the real ON DELETE CASCADE does the rest


class RealDB:
    def __init__(self):
        self.rest = rest_client(role_key("service_role"))
        self.users = {}
        self.auth = SimpleNamespace(admin=PgAdmin(self))

    def table(self, name):
        return self.rest.table(name)

    def rpc(self, name, params):
        return self.rest.rpc(name, params)


@pytest.fixture
def db(monkeypatch):   # overrides the fake-DB fixture from conftest for every test in this file
    sql("truncate public.likes, public.blocks, public.profiles, public.accounts, auth.users cascade")
    real = RealDB()
    monkeypatch.setattr(main, "supabase", real)
    main._cache.clear()
    main._hits.clear()
    return real


def rows(table, where="true"):
    return sql(f"select count(*) from public.{table} where {where}", fetch=True)[0][0]


def mutual(api, a, a_name, b, b_name, game="cs2"):
    api.post("/api/like", user=a, json={"to_user": b_name, "game": game})
    api.post("/api/like", user=b, json={"to_user": a_name, "game": game})


# ---------------------------------------------------------------------------------------------- browser roles
def test_browser_roles_can_read_or_call_nothing(users, make_profile):
    make_profile(users["alice"], "Alice", in_game_username="AliceCS")
    from postgrest.exceptions import APIError
    for token in (role_key("anon"), make_token(users["alice"], role="authenticated")):
        c = rest_client(token)
        for t in ("profiles", "likes", "blocks", "accounts"):
            assert c.table(t).select("*").execute().data == []           # RLS on, no policies
        with pytest.raises(APIError) as e:
            c.rpc("social_snapshot", {"viewer": users["alice"], "g": "cs2"}).execute()
        assert "permission denied" in str(e.value)
        with pytest.raises(APIError) as e:
            c.rpc("delete_account_data", {"uid": users["alice"]}).execute()
        assert "permission denied" in str(e.value)
        with pytest.raises(APIError):
            c.table("likes").insert({"from_user_id": users["alice"], "to_user_id": users["bob"], "game": "cs2"}).execute()
    assert rows("likes") == 0 and rows("profiles") == 1 and rows("accounts") == 1


# ---------------------------------------------------------------------------------------------- main flows
def test_like_back_mutual_contact_unmatch_on_real_db(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice", in_game_username="AliceCS")
    make_profile(b, "Bob", in_game_username="BobCS", discord_username="bob_dc")
    api.post("/api/like", user=b, json={"to_user": "alice", "game": "cs2"})
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert [p["username"] for p in d["incoming"]] == ["bob"] and "BobCS" not in str(d)
    assert api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})[1]["status"] == "mutual"
    assert api.post("/api/like", user=a, json={"to_user": "bob", "game": "cs2"})[1]["status"] == "already_exists"
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert d["squadmates"][0]["in_game_username"] == "BobCS" and d["squadmates"][0]["discord_username"] == "bob_dc"
    assert rows("likes") == 2
    api.delete("/api/like?to_user=bob&game=cs2", user=a)
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert d["squadmates"] == [] and d["incoming"] == [] and rows("likes") == 0


def test_real_unique_violations_are_recognised(users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    like = {"from_user": "alice", "to_user": "bob", "from_user_id": users["alice"], "to_user_id": users["bob"], "game": "cs2"}
    db.table("likes").insert(like).execute()
    with pytest.raises(Exception) as e:
        db.table("likes").insert(like).execute()
    assert main.is_unique_violation(e.value) and "duplicate key" in str(e.value)


def test_username_claim_race_on_two_connections(users, db):
    """Two different people save the same new name at the same moment: exactly one gets it."""
    from fastapi.testclient import TestClient
    body = {"region": "middle-east", "country": "Iran", "city": "Tehran", "mic": "voice", "languages": "fa",
            "game": "cs2", "platform": "PC", "fields": {"mode": "Premier", "rank": "Silver"}}
    for i in range(5):
        name = f"race{i}"
        racers = [db.auth.admin.create_user(email=f"r{i}{k}@example.com") for k in range(2)]
        results, start = [], threading.Barrier(2)

        def save(uid):
            client = TestClient(main.app, raise_server_exceptions=False)
            start.wait()
            r = client.post("/api/profile", json={**body, "username": name},
                            headers={"Authorization": "Bearer " + make_token(uid)})
            results.append(r.status_code)
        threads = [threading.Thread(target=save, args=(u,)) for u in racers]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert sorted(results) == [200, 409], results
        assert rows("accounts", f"username = '{name}'") == 1 and rows("profiles", f"username = '{name}'") == 1


def test_report_is_monotonic_on_real_db(api, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2", "report": True, "reason": "Cheating"})
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.post("/api/block", user=users["alice"], json={"to_user": "bob", "game": "cs2", "report": True, "reason": ""})
    assert api.delete("/api/block?to_user=bob", user=users["alice"])[0] == 409
    assert sql("select reported, reason from public.blocks", fetch=True) == [(True, "Cheating")]


# ---------------------------------------------------------------------------------------------- social_snapshot SQL
def test_snapshot_blocks_cross_games_and_flag(api, users, make_profile, db):
    a, b, c = users["alice"], users["bob"], users["carol"]
    make_profile(a, "Alice")
    make_profile(b, "Bob", in_game_username="BobCS")
    make_profile(c, "Carol")
    make_profile(a, "Alice", "gta")
    make_profile(b, "Bob", "gta")
    mutual(api, a, "alice", b, "bob")
    mutual(api, a, "alice", c, "carol")
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "gta"})   # blocked in ANOTHER game
    snap = db.rpc("social_snapshot", {"viewer": a, "g": "cs2"}).execute().data
    assert snap["blocked"] == [b]
    assert {p["username"] for p in snap["profiles"]} == {"carol"}             # bob's profile never leaves the DB
    assert len(snap["likes"]) == 4
    bare = db.rpc("social_snapshot", {"viewer": a, "g": "cs2", "with_profiles": False}).execute().data
    assert bare["profiles"] == [] and len(bare["likes"]) == 4
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert [m["username"] for m in d["squadmates"]] == ["carol"] and "BobCS" not in str(d)
    empty = db.rpc("social_snapshot", {"viewer": users["alice"], "g": "minecraft"}).execute().data
    assert empty == {"likes": [], "blocked": [b], "profiles": []}


def test_snapshot_ignores_legacy_null_rows(api, users, make_profile, db):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob")
    mutual(api, a, "alice", b, "bob")
    # rows from the very first app version: likes by name only, a profile without a user id
    sql("insert into public.likes (from_user, to_user, game) values ('ghost', 'alice', 'cs2'), ('alice', 'ghost2', 'cs2')")
    sql("insert into public.likes (from_user, to_user, game, to_user_id) values ('ghost3', 'alice', 'cs2', %s)", (a,))  # legacy: no from id
    sql("insert into public.profiles (username, game) values ('ghost', 'cs2')")
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert [m["username"] for m in d["squadmates"]] == ["bob"] and d["incoming"] == []


def test_600_mutual_pairs_are_all_squadmates(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice")
    sql("""
        with u as (select gen_random_uuid() id, n from generate_series(1, 600) n),
        au as (insert into auth.users (id) select id from u),
        p as (insert into public.profiles (username, display_username, game, region, user_id, game_meta)
              select 'p' || n, 'p' || n, 'cs2', 'middle-east', id, '{}' from u returning user_id, username)
        insert into public.likes (from_user, to_user, from_user_id, to_user_id, game)
        select 'alice', p.username, %(a)s::uuid, p.user_id, 'cs2' from p
        union all select p.username, 'alice', p.user_id, %(a)s::uuid, 'cs2' from p
    """, {"a": a})
    assert rows("likes") == 1200
    _, d = api.get("/api/poll?game=cs2", user=a)
    assert len(d["squadmates"]) == 600 and d["pending"] == [] and d["incoming"] == []
    main._cache.clear()
    _, g = api.get("/api/games")
    assert {x["id"]: x["players"] for x in g["games"]}["cs2"] == 601   # exact HEAD count (the 1000-row page case: fake suite)


def test_account_deletion_leaves_nothing(api, users, make_profile):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(a, "Alice", "gta")
    make_profile(b, "Bob")
    mutual(api, a, "alice", b, "bob")
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "cs2", "report": True, "reason": "Spam"})
    assert api.delete("/api/account", user=a, json={"confirm": "DELETE"})[0] == 200
    assert rows("profiles", f"user_id = '{a}'") == 0 and rows("accounts", f"user_id = '{a}'") == 0
    assert rows("likes") == 0 and rows("blocks") == 0
    assert sql("select count(*) from auth.users where id = %s", (a,), fetch=True)[0][0] == 0
    assert api.client.get("/u/alice").status_code == 404


def test_set_profile_avatar_changes_only_the_avatar_key(api, users, make_profile, db):
    a = users["alice"]
    make_profile(a, "Alice", fields={"mode": "Premier", "rank": "Gold Nova"})
    make_profile(a, "Alice", "gta")
    assert db.rpc("set_profile_avatar", {"uid": a, "a": "avatar-4"}).execute().data == 2
    assert db.rpc("set_profile_avatar", {"uid": a, "a": "avatar-4"}).execute().data == 0   # nothing to change
    metas = dict(sql("select game, game_meta from public.profiles where user_id = %s", (a,), fetch=True))
    assert metas["cs2"]["avatar"] == "avatar-4" and metas["cs2"]["fields"] == {"mode": "Premier", "rank": "Gold Nova"}
    assert db.rpc("set_profile_avatar", {"uid": a, "a": ""}).execute().data == 2
    metas = dict(sql("select game, game_meta from public.profiles where user_id = %s", (a,), fetch=True))
    assert "avatar" not in metas["cs2"] and metas["cs2"]["country"] == "Iran"
    from postgrest.exceptions import APIError
    with pytest.raises(APIError):
        rest_client(make_token(a, role="authenticated")).rpc("set_profile_avatar", {"uid": a, "a": "avatar-1"}).execute()



# ---------------------------------------------------------------------------------------------- migration 005
def test_late_rows_for_a_deleted_user_are_refused_and_auth_deletion_cascades(api, users, make_profile, db):
    a, b = users["alice"], users["bob"]
    make_profile(a, "Alice")
    make_profile(b, "Bob")
    mutual(api, a, "alice", b, "bob")
    api.post("/api/block", user=b, json={"to_user": "alice", "game": "gta"})
    sql("delete from auth.users where id = %s", (a,))            # cascade: everything of alice goes with the login
    assert rows("profiles", f"user_id = '{a}'") == 0 and rows("likes") == 0 and rows("blocks") == 0
    import psycopg
    for stmt in ("insert into public.profiles (username, game, user_id) values ('ghost', 'cs2', %s)",
                 "insert into public.likes (from_user, to_user, game, from_user_id, to_user_id) values ('x', 'bob', 'cs2', %s, '%s')" % ("%s", b),
                 "insert into public.blocks (blocker_id, blocked_id) values (%s, '%s')" % ("%s", b)):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            sql(stmt, (a,))
    status, d = api.post("/api/profile", user=a, json={
        "username": "Alice", "game": "cs2", "platform": "PC", "region": "middle-east", "country": "Iran",
        "mic": "voice", "languages": "fa", "fields": {"mode": "Premier", "rank": "Silver"}})
    assert status == 401 and rows("profiles", f"user_id = '{a}'") == 0   # a stale token's save is refused


def test_avatar_changes_and_copies_are_serialized(users, make_profile, db):
    """Two transactions: an avatar change holding the account row, and a copy (from a profile save) started meanwhile.
    The copy waits and then uses the NEW avatar; profiles always end equal to accounts.avatar."""
    import psycopg
    a = users["alice"]
    make_profile(a, "Alice")
    make_profile(a, "Alice", "gta")
    sql("select public.set_account_avatar(%s, 'avatar-1')", (a,))
    t1 = psycopg.connect(PG_URL)
    t1.execute("select public.set_account_avatar(%s, 'avatar-3')", (a,))   # not committed yet: holds the row lock
    done = {}

    def copy_from_a_profile_save():
        with psycopg.connect(PG_URL, autocommit=True) as t2:
            done["n"] = t2.execute("select public.sync_profile_avatar(%s)", (a,)).fetchone()[0]
    th = threading.Thread(target=copy_from_a_profile_save)
    th.start()
    th.join(1.0)
    assert th.is_alive()                     # it waits for the avatar change instead of copying the old value
    t1.commit()
    t1.close()
    th.join(5)
    avatars = {r[0] for r in sql("select game_meta ->> 'avatar' from public.profiles where user_id = %s", (a,), fetch=True)}
    assert avatars == {"avatar-3"} == {sql("select avatar from public.accounts where user_id = %s", (a,), fetch=True)[0][0]}
    # two changes at the same time: whichever commits last wins — everywhere
    c1, c2 = psycopg.connect(PG_URL), psycopg.connect(PG_URL)
    c1.execute("select public.set_account_avatar(%s, 'avatar-5')", (a,))
    th = threading.Thread(target=lambda: (c2.execute("select public.set_account_avatar(%s, 'avatar-8')", (a,)), c2.commit()))
    th.start()
    th.join(1.0)
    c1.commit()
    th.join(5)
    c1.close(); c2.close()
    acc = sql("select avatar from public.accounts where user_id = %s", (a,), fetch=True)[0][0]
    avatars = {r[0] for r in sql("select game_meta ->> 'avatar' from public.profiles where user_id = %s", (a,), fetch=True)}
    assert acc == "avatar-8" and avatars == {"avatar-8"}


def test_avatar_functions_are_server_only(users, make_profile):
    from postgrest.exceptions import APIError
    make_profile(users["alice"], "Alice")
    for token in (role_key("anon"), make_token(users["alice"], role="authenticated")):
        for fn, params in (("set_account_avatar", {"uid": users["alice"], "a": "avatar-1"}),
                           ("sync_profile_avatar", {"uid": users["alice"]})):
            with pytest.raises(APIError) as e:
                rest_client(token).rpc(fn, params).execute()
            assert "permission denied" in str(e.value)
