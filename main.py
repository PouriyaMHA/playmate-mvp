"""PlayMate API + pages (FastAPI).

Identity always comes from the Supabase JWT (user_id), never from request bodies.
Per-game profiles live in `profiles` (unique user_id + game); account-level data
(bio, banner, avatar, links, referral) lives in the auth user's app_metadata["playmate"],
which only the server (secret key) can write.
"""
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jwt import PyJWTError
from pydantic import BaseModel
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

from games import GAME_ORDER, GAMES, clean_fields, game_meta, game_summary, get_game, region_label

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
if not SUPABASE_JWT_SECRET:
    print("WARNING: SUPABASE_JWT_SECRET is missing. Auth endpoints will fail.")

# Own HTTP client for Supabase: the default HTTP/2 connection goes stale after being idle and the
# next request fails with "Server disconnected" (random 500s). HTTP/1.1 + short keep-alive + retries avoids it.
_supabase_http = httpx.Client(
    http2=False,
    timeout=30,
    follow_redirects=True,
    limits=httpx.Limits(keepalive_expiry=20),
    transport=httpx.HTTPTransport(retries=2),
)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=SyncClientOptions(httpx_client=_supabase_http))

app = FastAPI(title="PlayMate")
API_PREFIX = "/api"

# CSS / JS / images (bump the ?v= in the HTML when these change, to bust browser caches)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

DEFAULT_GAME = "battlefield"
EARLY_MEMBER_BEFORE = datetime(2027, 1, 1, tzinfo=timezone.utc)
BANNERS = [f"banner-{i}" for i in range(1, 9)]
AVATARS = [f"avatar-{i}" for i in range(1, 13)]

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,24}$")
FREE_TEXT_RE = re.compile(r"^[^<>\"'`]{1,40}$")  # IGN / Discord / handles: no HTML-ish characters
VOICE = {"voice", "both"}

# Fields of another player that are safe to show anywhere public (never in_game_username / discord)
PUBLIC_PROFILE_FIELDS = (
    "username,display_username,game,platform,region,city,languages,mic,"
    "favorite_mode,class_type,game_meta,created_at,last_active,looking_until"
)


# =========================================================
# helpers
# =========================================================
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def is_looking_now(looking_until) -> bool:
    ts = parse_ts(looking_until)
    return bool(ts and ts > now_utc())


def norm_game(game: str | None) -> str:
    g = (game or DEFAULT_GAME).strip().lower()
    if g not in GAMES:
        raise HTTPException(status_code=400, detail="Unsupported game")
    return g


def parse_languages(lang_str: str | None) -> list[str]:
    return [x.strip().lower() for x in (lang_str or "").split(",") if x.strip()]


def clean_optional_text(value: str | None, field: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    if not FREE_TEXT_RE.match(v):
        raise HTTPException(status_code=422, detail=f"{field} must be 1-40 characters and cannot contain < > \" ' `")
    return v


def profile_fields(p: dict) -> dict:
    """Game-specific field values of a profile row (with Battlefield's old columns as fallback)."""
    fields = dict(((p.get("game_meta") or {}).get("fields")) or {})
    g = GAMES.get(p.get("game") or "")
    if g:
        for f in g["fields"]:
            col = f.get("column")
            if col and not fields.get(f["id"]) and p.get(col):
                fields[f["id"]] = p[col]
    return fields


def public_view(p: dict) -> dict:
    """A profile row as other players may see it."""
    return {
        "username": p.get("username"),
        "display_username": p.get("display_username") or p.get("username"),
        "game": p.get("game"),
        "platform": p.get("platform"),
        "region": p.get("region"),
        "city": p.get("city"),
        "languages": p.get("languages"),
        "mic": p.get("mic"),
        "fields": profile_fields(p),
        # kept for older clients
        "favorite_mode": p.get("favorite_mode"),
        "class_type": p.get("class_type"),
        "last_active": p.get("last_active"),
        "looking_now": is_looking_now(p.get("looking_until")),
    }


def get_blocked_ids(user_id: str) -> set[str]:
    """Users I blocked + users who blocked me. A block hides both people from each other in every game."""
    res = (
        supabase.table("blocks")
        .select("blocker_id,blocked_id")
        .or_(f"blocker_id.eq.{user_id},blocked_id.eq.{user_id}")
        .execute()
    )
    out: set[str] = set()
    for r in res.data or []:
        other = r["blocked_id"] if str(r["blocker_id"]) == user_id else r["blocker_id"]
        out.add(str(other))
    return out


def my_profile_row(user_id: str, game: str, columns: str = "*") -> dict | None:
    res = supabase.table("profiles").select(columns).eq("user_id", user_id).eq("game", game).limit(1).execute()
    return res.data[0] if res.data else None


def require_profile(user_id: str, game: str, columns: str = "*") -> dict:
    row = my_profile_row(user_id, game, columns)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found for this user")
    return row


def mutual_ids(user_id: str, game: str) -> list[str]:
    out_res = supabase.table("likes").select("to_user_id").eq("from_user_id", user_id).eq("game", game).execute()
    outgoing = [str(r["to_user_id"]) for r in (out_res.data or []) if r.get("to_user_id")]
    if not outgoing:
        return []
    in_res = (
        supabase.table("likes").select("from_user_id")
        .eq("to_user_id", user_id).eq("game", game).in_("from_user_id", outgoing).execute()
    )
    return [str(r["from_user_id"]) for r in (in_res.data or []) if r.get("from_user_id")]


def user_id_for_username(username: str) -> str | None:
    u = (username or "").strip().lower()
    if not u:
        return None
    res = supabase.table("profiles").select("user_id").eq("username", u).limit(1).execute()
    return str(res.data[0]["user_id"]) if res.data and res.data[0].get("user_id") else None


def auth_user(user_id: str):
    try:
        return supabase.auth.admin.get_user_by_id(user_id).user
    except Exception:
        return None


def account_data(user) -> dict:
    meta = (getattr(user, "app_metadata", None) or {}).get("playmate") or {}
    return {
        "bio": meta.get("bio") or "",
        "banner": meta.get("banner") if meta.get("banner") in BANNERS else "banner-1",
        "avatar": meta.get("avatar") if meta.get("avatar") in AVATARS else "",
        "links": {k: v for k, v in (meta.get("links") or {}).items() if k in ("twitch", "youtube", "instagram", "steam")},
        "referred_by": meta.get("referred_by"),
    }


def save_account_meta(user, changes: dict) -> dict:
    app_meta = dict(getattr(user, "app_metadata", None) or {})
    playmate = dict(app_meta.get("playmate") or {})
    playmate.update(changes)
    app_meta["playmate"] = playmate
    supabase.auth.admin.update_user_by_id(user.id, {"app_metadata": app_meta})
    return playmate


def badges_for(user, mutual_count: int) -> list[dict]:
    created = parse_ts(getattr(user, "created_at", None)) if user else None
    return [
        {"id": "early-member", "label": "Early Member", "desc": "Joined PlayMate in its first months",
         "earned": bool(created and created < EARLY_MEMBER_BEFORE)},
        {"id": "first-match", "label": "First Match", "desc": "Made a first mutual match", "earned": mutual_count >= 1},
        {"id": "squad-leader", "label": "Squad Leader", "desc": "5 or more squadmates", "earned": mutual_count >= 5},
        {"id": "verified", "label": "Verified", "desc": "Coming soon", "earned": False},
        {"id": "legendary", "label": "Legendary", "desc": "Coming soon", "earned": False},
    ]


# =========================================================
# auth
# =========================================================
def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    """Reads the Supabase access token from the Authorization header and returns user_id (sub)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server missing SUPABASE_JWT_SECRET")
    try:
        payload = jwt.decode(parts[1].strip(), SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub")
    return str(user_id)


# =========================================================
# pages
# =========================================================
def page(name: str) -> HTMLResponse:
    return HTMLResponse((BASE_DIR / name).read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
def landing_page():
    return page("landing.html")


@app.get("/app", response_class=HTMLResponse)
@app.get("/bf", response_class=HTMLResponse)
def app_page():
    return page("ui.html")


@app.get("/ui")
def ui_redirect():
    return RedirectResponse(url="/app", status_code=302)


@app.get("/profile", response_class=HTMLResponse)
@app.get("/u/{username}", response_class=HTMLResponse)
def profile_page(username: str | None = None):
    return page("profile.html")


@app.get("/health")
def health(deep: bool = False):
    # deep=1 also touches the database (used by keep-alive pings so Supabase doesn't pause)
    if deep:
        supabase.table("profiles").select("id").limit(1).execute()
    return {"status": "ok"}


# =========================================================
# games / meta (public)
# =========================================================
@app.get(f"{API_PREFIX}/games")
def list_games():
    counts: dict[str, int] = {}
    rows = supabase.table("profiles").select("game").execute().data or []
    for r in rows:
        counts[r["game"]] = counts.get(r["game"], 0) + 1
    return {"games": [{**game_summary(g), "players": counts.get(g, 0)} for g in GAME_ORDER]}


@app.get(f"{API_PREFIX}/meta/{{game}}")
def get_game_meta(game: str):
    return game_meta(norm_game(game))


@app.get(f"{API_PREFIX}/stats")
def stats(game: str = DEFAULT_GAME, region: str | None = None):
    """Small 'the site is alive' numbers for empty states."""
    game = norm_game(game)
    rows = supabase.table("profiles").select("region,looking_until,last_active").eq("game", game).execute().data or []
    day_ago = now_utc() - timedelta(days=1)
    return {
        "game": game,
        "players": len(rows),
        "in_region": sum(1 for r in rows if region and r.get("region") == region),
        "looking_now": sum(1 for r in rows if is_looking_now(r.get("looking_until"))),
        "active_today": sum(1 for r in rows if (parse_ts(r.get("last_active")) or datetime.min.replace(tzinfo=timezone.utc)) > day_ago),
    }


# =========================================================
# my per-game profiles
# =========================================================
class ProfileIn(BaseModel):
    username: str | None = None
    game: str | None = DEFAULT_GAME
    in_game_username: str | None = None
    discord_username: str | None = None
    platform: str | None = None
    region: str | None = None
    city: str | None = None
    mic: str | None = None
    languages: str | None = None
    fields: dict | None = None
    # older Battlefield clients
    favorite_mode: str | None = None
    class_type: str | None = None


@app.post(f"{API_PREFIX}/profile")
def save_profile(profile: ProfileIn, user_id: str = Depends(get_current_user_id)):
    game = norm_game(profile.game)
    g = GAMES[game]

    # username: locked once chosen (same name in every game)
    existing = my_profile_row(user_id, game, "username,display_username")
    if not existing:
        any_game = supabase.table("profiles").select("username,display_username").eq("user_id", user_id).limit(1).execute()
        existing = any_game.data[0] if any_game.data else None
    if existing:
        username = (existing.get("username") or "").strip().lower()
        display_username = existing.get("display_username") or username
        locked = True
    else:
        raw = (profile.username or "").strip()
        if not USERNAME_RE.match(raw):
            raise HTTPException(status_code=422, detail="Username must be 3-24 characters: letters, numbers, _ . -")
        taken = supabase.table("profiles").select("user_id").eq("username", raw.lower()).neq("user_id", user_id).limit(1).execute()
        if taken.data:
            raise HTTPException(status_code=409, detail="This PlayMate username is already taken.")
        username, display_username, locked = raw.lower(), raw, False

    # common fields
    missing = []
    region = (profile.region or "").strip()
    if not region:
        missing.append("Region")
    mic = (profile.mic or "").strip()
    if mic not in ("voice", "both", "none"):
        missing.append("Mic")
    languages = ",".join(parse_languages(profile.languages))
    if not languages:
        missing.append("Languages")
    platform = (profile.platform or "").strip() or None
    if platform and platform not in g["platforms"]:
        platform = None

    raw_fields = dict(profile.fields or {})
    if profile.favorite_mode and "favorite_mode" not in raw_fields:
        raw_fields["favorite_mode"] = profile.favorite_mode
    if profile.class_type and "class_type" not in raw_fields:
        raw_fields["class_type"] = profile.class_type
    fields, missing_fields = clean_fields(game, raw_fields)
    missing += missing_fields
    if missing:
        raise HTTPException(status_code=422, detail="Missing required fields: " + ", ".join(missing))

    payload = {
        "user_id": user_id,
        "username": username,
        "display_username": display_username,
        "game": game,
        "in_game_username": clean_optional_text(profile.in_game_username, g["ign_label"]),
        "discord_username": clean_optional_text(profile.discord_username, "Discord username"),
        "platform": platform,
        "region": region,
        "city": (profile.city or "").strip()[:40] or None,
        "mic": mic,
        "languages": languages,
        "game_meta": {"fields": fields},
    }
    for f in g["fields"]:
        if f.get("column"):
            payload[f["column"]] = fields.get(f["id"])

    try:
        result = supabase.table("profiles").upsert(payload, on_conflict="user_id,game").execute()
    except Exception as e:
        msg = str(e)
        if "profiles_game_ign_unique" in msg:
            raise HTTPException(status_code=409, detail=f"This {g['ign_label']} is already used by another PlayMate player.")
        if "duplicate key" in msg:
            raise HTTPException(status_code=409, detail="This username is already taken.")
        raise
    saved = result.data[0] if result.data else payload
    return {"status": "saved", "locked_username": locked, "data": saved}


@app.delete(f"{API_PREFIX}/profile")
def delete_game_profile(game: str, user_id: str = Depends(get_current_user_id)):
    """Remove one game from my profile (my likes in that game go too)."""
    game = norm_game(game)
    supabase.table("likes").delete().eq("from_user_id", user_id).eq("game", game).execute()
    supabase.table("likes").delete().eq("to_user_id", user_id).eq("game", game).execute()
    supabase.table("profiles").delete().eq("user_id", user_id).eq("game", game).execute()
    return {"status": "deleted", "game": game}


@app.get(f"{API_PREFIX}/my-profile")
def my_profile(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    """My own profile for one game (incl. private in_game_username / discord), to restore the form anywhere."""
    row = require_profile(user_id, norm_game(game))
    out = public_view(row)
    out.update({
        "in_game_username": row.get("in_game_username"),
        "discord_username": row.get("discord_username"),
        "looking_until": row.get("looking_until"),
    })
    return out


@app.get(f"{API_PREFIX}/my-games")
def my_games(user_id: str = Depends(get_current_user_id)):
    rows = supabase.table("profiles").select("game,username,display_username").eq("user_id", user_id).execute().data or []
    username = rows[0]["username"] if rows else None
    return {
        "username": username,
        "display_username": rows[0].get("display_username") if rows else None,
        "games": [r["game"] for r in rows if r.get("game") in GAMES],
    }


@app.post(f"{API_PREFIX}/ping")
def ping(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    game = norm_game(game)
    me = require_profile(user_id, game, "username,display_username")
    now_iso = now_utc().isoformat()
    supabase.table("profiles").update({"last_active": now_iso}).eq("user_id", user_id).eq("game", game).execute()
    return {
        "status": "ok",
        "username": me.get("username"),
        "display_username": me.get("display_username") or me.get("username"),
        "game": game,
        "last_active": now_iso,
    }


class LookingRequest(BaseModel):
    minutes: int = 60          # 0 = stop looking
    game: str | None = DEFAULT_GAME


@app.post(f"{API_PREFIX}/looking")
def set_looking(req: LookingRequest, user_id: str = Depends(get_current_user_id)):
    """Toggle "Looking for a squad now" for a limited time (max 3h)."""
    game = norm_game(req.game)
    minutes = max(0, min(int(req.minutes or 0), 180))
    until = (now_utc() + timedelta(minutes=minutes)).isoformat() if minutes else None
    res = supabase.table("profiles").update({"looking_until": until}).eq("user_id", user_id).eq("game", game).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")
    return {"looking_now": bool(until), "looking_until": until}


# =========================================================
# matching
# =========================================================
class MatchRequest(BaseModel):
    game: str | None = DEFAULT_GAME
    same_language_only: bool = False
    looking_only: bool = False


def score_pair(me: dict, other: dict, game: str) -> tuple[int, list[str]]:
    g = GAMES[game]
    score, reasons = 0, []

    if me.get("region") and other.get("region") == me.get("region"):
        score += 35
        reasons.append(f"Same region: {region_label(me['region'])}")
        if me.get("city") and other.get("city") == me.get("city"):
            score += 5
            reasons.append(f"Same city: {me['city']}")

    langs = sorted(set(parse_languages(me.get("languages"))) & set(parse_languages(other.get("languages"))))
    if langs:
        score += 15 + min(5, 5 * (len(langs) - 1))
        reasons.append("Speaks " + ", ".join(langs))

    if (me.get("mic") or "") in VOICE and (other.get("mic") or "") in VOICE:
        score += 10
        reasons.append("Both use voice chat")

    if len(g["platforms"]) > 1 and me.get("platform") and other.get("platform") == me.get("platform"):
        score += 5
        reasons.append(f"Same platform: {me['platform']}")

    mine, theirs = profile_fields(me), profile_fields(other)
    for f in g["fields"]:
        v = mine.get(f["id"])
        if v and theirs.get(f["id"]) == v:
            score += f["weight"]
            reasons.append(f"Same {f['label'].lower()}: {v}")

    return min(score, 100), reasons


@app.post(f"{API_PREFIX}/match")
def match_players(req: MatchRequest, user_id: str = Depends(get_current_user_id)):
    """Ranks other players of the same game against MY saved profile (the request only carries options)."""
    game = norm_game(req.game)
    me = require_profile(user_id, game)
    my_langs = set(parse_languages(me.get("languages")))

    liked = supabase.table("likes").select("to_user_id").eq("from_user_id", user_id).eq("game", game).execute()
    hidden = {str(r["to_user_id"]) for r in (liked.data or []) if r.get("to_user_id")} | get_blocked_ids(user_id) | {user_id}

    players = supabase.table("profiles").select("*").eq("game", game).execute().data or []
    matches = []
    for p in players:
        if not p.get("user_id") or str(p["user_id"]) in hidden:
            continue
        if req.same_language_only and not (my_langs & set(parse_languages(p.get("languages")))):
            continue
        view = public_view(p)
        if req.looking_only and not view["looking_now"]:
            continue
        score, reasons = score_pair(me, p, game)
        if view["looking_now"]:
            reasons.insert(0, "Looking for a squad right now")
        matches.append({
            "username": p.get("username"),
            "match_percent": score,
            "reasons": reasons,
            "looking_now": view["looking_now"],
            "profile": view,
        })

    # players looking right now first, then by score
    matches.sort(key=lambda m: (m["looking_now"], m["match_percent"]), reverse=True)
    return {"target_user": me.get("username"), "game": game, "total": len(matches), "matches": matches[:20]}


# =========================================================
# likes / squad
# =========================================================
class LikeRequest(BaseModel):
    to_user: str
    game: str | None = DEFAULT_GAME
    from_user: str | None = None   # ignored (identity comes from the token)


@app.post(f"{API_PREFIX}/like")
def add_like(like: LikeRequest, user_id: str = Depends(get_current_user_id)):
    game = norm_game(like.game)
    to_user = (like.to_user or "").strip().lower()
    if not to_user:
        raise HTTPException(status_code=400, detail="to_user is required")

    me = require_profile(user_id, game, "username")
    from_user = (me.get("username") or "").strip().lower()
    if from_user == to_user:
        raise HTTPException(status_code=400, detail="You cannot like yourself")

    target = supabase.table("profiles").select("user_id").eq("username", to_user).eq("game", game).limit(1).execute()
    if not target.data or not target.data[0].get("user_id"):
        raise HTTPException(status_code=404, detail="Target user not found")
    to_user_id = str(target.data[0]["user_id"])
    if to_user_id in get_blocked_ids(user_id):
        raise HTTPException(status_code=403, detail="You can't like this player")

    payload = {"from_user": from_user, "to_user": to_user, "from_user_id": user_id, "to_user_id": to_user_id, "game": game}
    reverse = (
        supabase.table("likes").select("id")
        .eq("from_user_id", to_user_id).eq("to_user_id", user_id).eq("game", game).limit(1).execute()
    )
    mutual = bool(reverse.data)
    exists = (
        supabase.table("likes").select("id")
        .eq("from_user_id", user_id).eq("to_user_id", to_user_id).eq("game", game).limit(1).execute()
    )
    if exists.data:
        return {"status": "already_exists", "mutual": mutual, "data": payload}

    supabase.table("likes").insert(payload).execute()
    return {"status": "mutual" if mutual else "liked", "mutual": mutual, "data": payload}


@app.get(f"{API_PREFIX}/my-squad-details")
def my_squad_details(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    game = norm_game(game)
    me = require_profile(user_id, game, "username")
    blocked = get_blocked_ids(user_id)
    ids = [i for i in mutual_ids(user_id, game) if i not in blocked]
    if not ids:
        return {"username": me.get("username"), "game": game, "squadmates": []}

    rows = (
        supabase.table("profiles")
        .select("*").eq("game", game).in_("user_id", ids).execute().data or []
    )
    mates = []
    for p in rows:
        v = public_view(p)
        # mutual squadmates may see how to reach each other
        v["in_game_username"] = p.get("in_game_username")
        v["discord_username"] = p.get("discord_username")
        mates.append(v)
    return {"username": me.get("username"), "game": game, "squadmates": mates}


@app.get(f"{API_PREFIX}/pending-likes")
def pending_likes(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    """People I liked who haven't liked me back yet (no in-game name: not mutual)."""
    game = norm_game(game)
    out_res = supabase.table("likes").select("to_user_id,created_at").eq("from_user_id", user_id).eq("game", game).execute()
    liked_at = {str(r["to_user_id"]): r.get("created_at") for r in (out_res.data or []) if r.get("to_user_id")}
    if not liked_at:
        return {"game": game, "pending": []}

    mutual = set(mutual_ids(user_id, game))
    blocked = get_blocked_ids(user_id)
    pending_ids = [uid for uid in liked_at if uid not in mutual and uid not in blocked]
    if not pending_ids:
        return {"game": game, "pending": []}

    rows = (
        supabase.table("profiles")
        .select("user_id,username,display_username,region,last_active,looking_until")
        .eq("game", game).in_("user_id", pending_ids).execute().data or []
    )
    pending = [{
        "username": p.get("username"),
        "display_username": p.get("display_username") or p.get("username"),
        "region": p.get("region"),
        "last_active": p.get("last_active"),
        "liked_at": liked_at.get(str(p["user_id"])),
    } for p in rows]
    pending.sort(key=lambda x: x.get("liked_at") or "", reverse=True)
    return {"game": game, "pending": pending}


class BlockRequest(BaseModel):
    to_user: str
    game: str | None = DEFAULT_GAME
    report: bool = False
    reason: str | None = None


@app.post(f"{API_PREFIX}/block")
def block_player(req: BlockRequest, user_id: str = Depends(get_current_user_id)):
    """Block (and optionally report) a player: both are hidden from each other everywhere from now on."""
    game = norm_game(req.game)
    blocked_id = user_id_for_username(req.to_user)
    if not blocked_id:
        raise HTTPException(status_code=404, detail="Player not found")
    if blocked_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")
    supabase.table("blocks").upsert(
        {
            "blocker_id": user_id,
            "blocked_id": blocked_id,
            "game": game,
            "reported": bool(req.report),
            "reason": (req.reason or "").strip()[:300] or None,
        },
        on_conflict="blocker_id,blocked_id,game",
    ).execute()
    return {"status": "blocked", "reported": bool(req.report)}


# =========================================================
# account (bio, banner, avatar, links, invites)
# =========================================================
class AccountUpdate(BaseModel):
    bio: str | None = None
    banner: str | None = None
    avatar: str | None = None
    links: dict | None = None


def my_account_payload(user_id: str) -> dict:
    user = auth_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    games = supabase.table("profiles").select("game,username,display_username").eq("user_id", user_id).execute().data or []
    username = games[0]["username"] if games else None
    mutual_count = sum(len(mutual_ids(user_id, r["game"])) for r in games)
    referrals = 0
    if username:
        try:
            for u in supabase.auth.admin.list_users(page=1, per_page=1000):
                if ((u.app_metadata or {}).get("playmate") or {}).get("referred_by") == username:
                    referrals += 1
        except Exception:
            pass
    return {
        **account_data(user),
        "username": username,
        "display_username": games[0].get("display_username") if games else None,
        "member_since": getattr(user, "created_at", None),
        "games": [r["game"] for r in games],
        "squad_count": mutual_count,
        "badges": badges_for(user, mutual_count),
        "invite_path": f"/?ref={username}" if username else None,
        "referrals": referrals,
    }


@app.get(f"{API_PREFIX}/account")
def get_account(user_id: str = Depends(get_current_user_id)):
    return my_account_payload(user_id)


@app.put(f"{API_PREFIX}/account")
def update_account(req: AccountUpdate, user_id: str = Depends(get_current_user_id)):
    user = auth_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    changes = {}
    if req.bio is not None:
        bio = req.bio.strip()
        if len(bio) > 280 or re.search(r"[<>]", bio):
            raise HTTPException(status_code=422, detail="Bio must be up to 280 characters and cannot contain < or >")
        changes["bio"] = bio
    if req.banner is not None:
        if req.banner not in BANNERS:
            raise HTTPException(status_code=422, detail="Unknown banner")
        changes["banner"] = req.banner
    if req.avatar is not None:
        if req.avatar and req.avatar not in AVATARS:
            raise HTTPException(status_code=422, detail="Unknown avatar")
        changes["avatar"] = req.avatar
    if req.links is not None:
        links = {}
        for k in ("twitch", "youtube", "instagram", "steam"):
            v = clean_optional_text((req.links or {}).get(k), k.capitalize())
            if v:
                links[k] = v
        changes["links"] = links
    if changes:
        save_account_meta(user, changes)
    return my_account_payload(user_id)


class ReferralRequest(BaseModel):
    ref: str


@app.post(f"{API_PREFIX}/account/referral")
def set_referral(req: ReferralRequest, user_id: str = Depends(get_current_user_id)):
    """Remember who invited me (only once, never myself)."""
    user = auth_user(user_id)
    ref = (req.ref or "").strip().lower()
    if not user or not USERNAME_RE.match(ref):
        return {"status": "ignored"}
    if account_data(user).get("referred_by"):
        return {"status": "already_set"}
    ref_id = user_id_for_username(ref)
    if not ref_id or ref_id == user_id:
        return {"status": "ignored"}
    save_account_meta(user, {"referred_by": ref})
    return {"status": "saved"}


# =========================================================
# public profile page data (no in-game names / discord)
# =========================================================
@app.get(f"{API_PREFIX}/public-profile")
def public_profile(username: str):
    uid = user_id_for_username(username)
    if not uid:
        raise HTTPException(status_code=404, detail="Player not found")
    user = auth_user(uid)
    rows = supabase.table("profiles").select(PUBLIC_PROFILE_FIELDS).eq("user_id", uid).execute().data or []
    mutual_count = sum(len(mutual_ids(uid, r["game"])) for r in rows)
    acc = account_data(user) if user else account_data(None)
    last_active = max((r.get("last_active") or "" for r in rows), default="") or None
    return {
        "username": rows[0]["username"] if rows else username.lower(),
        "display_username": (rows[0].get("display_username") or rows[0]["username"]) if rows else username,
        "bio": acc["bio"],
        "banner": acc["banner"],
        "avatar": acc["avatar"],
        "links": {k: v for k, v in acc["links"].items() if k != "steam"},
        "member_since": getattr(user, "created_at", None) if user else None,
        "last_active": last_active,
        "looking_now": any(is_looking_now(r.get("looking_until")) for r in rows),
        "squad_count": mutual_count,
        "badges": badges_for(user, mutual_count),
        "games": [{**game_summary(r["game"]), **public_view(r)} for r in rows if r.get("game") in GAMES],
    }


# old profile page endpoints (kept for compatibility)
@app.get("/profile-full")
def profile_full(username: str):
    u = (username or "").strip().lower()
    res = supabase.table("profiles").select(PUBLIC_PROFILE_FIELDS).eq("username", u).limit(1).execute()
    if not res.data:
        return {"error": "user not found"}
    return public_view(res.data[0])


@app.get("/profile-squad")
def profile_squad(username: str = Query(...), game: str = DEFAULT_GAME):
    game = norm_game(game)
    uid = user_id_for_username(username)
    if not uid:
        return {"username": username, "game": game, "squadmates": []}
    ids = mutual_ids(uid, game)
    if not ids:
        return {"username": username, "game": game, "squadmates": []}
    rows = supabase.table("profiles").select(PUBLIC_PROFILE_FIELDS).eq("game", game).in_("user_id", ids).execute().data or []
    # public endpoint: never expose in-game names / discord here
    return {"username": username, "game": game, "squadmates": [public_view(p) for p in rows]}
