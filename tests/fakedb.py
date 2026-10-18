"""In-memory stand-in for the parts of supabase-py that main.py uses, so API tests never touch the real database.

Covers: table().select/insert/upsert/update/delete with eq/neq/in_/or_/order/limit/execute (+ count="exact"),
and auth.admin.get_user_by_id/update_user_by_id/delete_user/create_user. Unique constraints mirror production
(see db/migrations): profiles (user_id, game) and (game, in_game_username); likes (from, to, game);
blocks (blocker, blocked, game); accounts (user_id), (username).
"""
import copy
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from supabase_auth.errors import AuthApiError

UNIQUE = {
    "profiles": [("user_id", "game"), ("game", "in_game_username")],
    "likes": [("from_user_id", "to_user_id", "game")],
    "blocks": [("blocker_id", "blocked_id", "game")],
    "accounts": [("user_id",), ("username",)],
}
DEFAULTS = {
    "profiles": {"game_meta": {}},
    "blocks": {"reported": False},
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _same(a, b):
    return a is not None and b is not None and str(a) == str(b)


class Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload, self.on_conflict = "select", None, None
        self.cols, self.want_count, self.head = "*", False, False
        self.filters, self.order_by, self.max_rows = [], None, None

    # ---- verbs
    def select(self, cols="*", count=None, head=False):
        self.op, self.cols, self.want_count, self.head = "select", cols, count == "exact", head
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.op, self.payload, self.on_conflict = "upsert", payload, on_conflict
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    # ---- filters
    def eq(self, col, val):
        self.filters.append(lambda r: _same(r.get(col), val))
        return self

    def neq(self, col, val):
        self.filters.append(lambda r: not _same(r.get(col), val))
        return self

    def gt(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and str(r.get(col)) > str(val))
        return self

    def in_(self, col, values):
        wanted = {str(v) for v in values}
        self.filters.append(lambda r: r.get(col) is not None and str(r.get(col)) in wanted)
        return self

    def or_(self, expr):
        parts = []
        for p in expr.split(","):
            col, op, val = p.split(".", 2)
            assert op == "eq", f"fake or_ only supports eq, got {op}"
            parts.append((col, val))
        self.filters.append(lambda r: any(_same(r.get(c), v) for c, v in parts))
        return self

    def order(self, col, desc=False, nullsfirst=False):
        self.order_by = (col, desc)
        return self

    def limit(self, n):
        self.max_rows = n
        return self

    # ---- run
    def _matches(self):
        return [r for r in self.db.tables.setdefault(self.table, []) if all(f(r) for f in self.filters)]

    def _project(self, row):
        if self.cols.strip() == "*":
            return copy.deepcopy(row)
        keep = [c.strip() for c in self.cols.split(",")]
        return {c: copy.deepcopy(row.get(c)) for c in keep}

    def _check_unique(self, row, ignore=None):
        for cols in UNIQUE.get(self.table, []):
            if any(row.get(c) is None for c in cols):
                continue
            for other in self.db.tables.setdefault(self.table, []):
                if other is ignore:
                    continue
                if all(_same(other.get(c), row.get(c)) for c in cols):
                    name = f"{self.table}_{'_'.join(cols)}_key"
                    if self.table == "profiles" and cols == ("game", "in_game_username"):
                        name = "profiles_game_ign_unique"
                    raise Exception(f'duplicate key value violates unique constraint "{name}"')

    def _new_row(self, payload):
        row = {"id": str(uuid.uuid4()), "created_at": _now(), **copy.deepcopy(DEFAULTS.get(self.table, {}))}
        row.update(copy.deepcopy(payload))
        return row

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "select":
            found = self._matches()
            if self.order_by:
                col, desc = self.order_by
                found.sort(key=lambda r: (r.get(col) is None, r.get(col) or ""), reverse=desc)
            count = len(found) if self.want_count else None
            if self.max_rows is not None:
                found = found[: self.max_rows]
            return Result([] if self.head else [self._project(r) for r in found], count)
        if self.op == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for p in items:
                row = self._new_row(p)
                self._check_unique(row)
                rows.append(row)
                out.append(copy.deepcopy(row))
            return Result(out)
        if self.op == "upsert":
            keys = [c.strip() for c in (self.on_conflict or "id").split(",")]
            p = self.payload
            existing = next((r for r in rows if all(_same(r.get(k), p.get(k)) for k in keys)), None)
            if existing:
                merged = {**existing, **copy.deepcopy(p)}
                self._check_unique(merged, ignore=existing)
                existing.update(copy.deepcopy(p))
                return Result([copy.deepcopy(existing)])
            row = self._new_row(p)
            self._check_unique(row)
            rows.append(row)
            return Result([copy.deepcopy(row)])
        if self.op == "update":
            out = []
            for r in self._matches():
                merged = {**r, **copy.deepcopy(self.payload)}
                self._check_unique(merged, ignore=r)
                r.update(copy.deepcopy(self.payload))
                out.append(copy.deepcopy(r))
            return Result(out)
        if self.op == "delete":
            gone = self._matches()
            self.db.tables[self.table] = [r for r in rows if r not in gone]
            return Result([copy.deepcopy(r) for r in gone])
        raise AssertionError(self.op)


class FakeAdmin:
    def __init__(self, db):
        self.db = db
        self.fail = False   # set True to simulate an Auth outage

    def _user(self, uid):
        if self.fail:
            raise RuntimeError("auth service down")
        u = self.db.users.get(str(uid))
        if not u:
            raise AuthApiError("User not found", 404, "user_not_found")
        return u

    def get_user_by_id(self, uid):
        return SimpleNamespace(user=copy.deepcopy(self._user(uid)))

    def update_user_by_id(self, uid, attrs):
        u = self._user(uid)
        if "app_metadata" in attrs:   # Supabase merges top-level keys; a None value removes the key
            for k, v in attrs["app_metadata"].items():
                if v is None:
                    u.app_metadata.pop(k, None)
                else:
                    u.app_metadata[k] = v
        return SimpleNamespace(user=copy.deepcopy(u))

    def delete_user(self, uid):
        self._user(uid)
        del self.db.users[str(uid)]

    def create_user(self, uid=None, email="", created_at=None):
        uid = uid or str(uuid.uuid4())
        self.db.users[uid] = SimpleNamespace(id=uid, email=email, created_at=created_at or _now(), app_metadata={})
        return uid


class FakeSupabase:
    def __init__(self):
        self.tables = {}
        self.users = {}
        self.auth = SimpleNamespace(admin=FakeAdmin(self))

    def table(self, name):
        return Query(self, name)
