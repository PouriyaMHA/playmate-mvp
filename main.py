"""PlayMate API + pages (FastAPI).

Identity always comes from the Supabase JWT (user_id), never from request bodies.
Per-game profiles live in `profiles` (unique user_id + game); account-level data
(bio, banner, avatar, links, referral) lives in the auth user's app_metadata["playmate"],
which only the server (secret key) can write.
"""
import html
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from jwt import PyJWTError
from pydantic import BaseModel
from supabase import create_client
from supabase_auth.errors import AuthApiError
from supabase.lib.client_options import SyncClientOptions

from games import (GAME_ORDER, GAMES, LANGUAGES, REGIONS, can_play_together, clean_fields, game_meta, game_summary,
                   region_label)
from locations import country_of_city, get_country

logger = logging.getLogger("playmate")

LANGUAGE_LABELS = {lang["code"]: lang["label"] for lang in LANGUAGES}

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

_SUPABASE_HOST = (os.getenv("SUPABASE_URL") or "").rstrip("/")
PUBLIC_URL = (os.getenv("PUBLIC_URL") or "https://playmate-api-aamc.onrender.com").rstrip("/")
# No inline scripts or inline event handlers anywhere, so scripts need no 'unsafe-inline'.
# (style-src keeps it for style="" attributes, which can't run code.)
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' https://unpkg.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    f"connect-src 'self' {_SUPABASE_HOST} {_SUPABASE_HOST.replace('https://', 'wss://')}".strip(),
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("Strict-Transport-Security", "max-age=31536000")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if "text/html" in h.get("content-type", ""):
        h.setdefault("Content-Security-Policy", CSP)
    if request.url.path.startswith(API_PREFIX + "/"):
        h["Cache-Control"] = "no-store"   # API answers can contain private data
    return response

# CSS / JS / images (bump the ?v= in the HTML when these change, to bust browser caches)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

DEFAULT_GAME = "battlefield"
EARLY_MEMBER_BEFORE = datetime(2027, 1, 1, tzinfo=timezone.utc)
BANNERS = [f"banner-{i}" for i in range(1, 9)]
AVATARS = [f"avatar-{i}" for i in range(1, 26)]  # 1-12 SVG art, 13+ illustrated WebP (see avatarSrc in profile.js)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,24}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
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


def clean_optional_text(value, field: str) -> str | None:
    v = ("" if value is None else str(value)).strip()
    if not v:
        return None
    if not FREE_TEXT_RE.match(v):
        raise HTTPException(status_code=422, detail=f"{field} must be 1-40 characters and cannot contain < > \" ' `")
    return v


def profile_fields(p: dict) -> dict:
    """Game-specific field values of a profile row, in the game's field order (with Battlefield's old columns
    as fallback). Values of fields the game no longer has (e.g. a removed "role") are left out."""
    stored = ((p.get("game_meta") or {}).get("fields")) or {}
    g = GAMES.get(p.get("game") or "")
    if not g:
        return dict(stored)
    fields = {}
    for f in g["fields"]:
        v = stored.get(f["id"]) or (p.get(f["column"]) if f.get("column") else None)
        if v:
            fields[f["id"]] = v
    return fields


def profile_country(p: dict) -> str | None:
    """Country saved with the profile, or (older profiles) the country of its city."""
    return ((p.get("game_meta") or {}).get("country")) or country_of_city(p.get("region"), p.get("city"))


def profile_avatar(p: dict) -> str:
    """The player's chosen avatar, copied onto each game profile (game_meta.avatar) so match lists need no extra lookups."""
    a = (p.get("game_meta") or {}).get("avatar")
    return a if a in AVATARS else ""


def current_avatar(user_id: str, existing_row: dict | None) -> str:
    """Account avatar for copying onto a game profile; if Auth is down, keep what the profile already had."""
    try:
        return account_data(auth_user(user_id)).get("avatar") or ""
    except HTTPException:
        return profile_avatar(existing_row or {})


def sync_profile_avatar(user_id: str, avatar: str) -> None:
    """Copy the account avatar onto every game profile of this user."""
    rows = supabase.table("profiles").select("id,game_meta").eq("user_id", user_id).execute().data or []
    for r in rows:
        meta = dict(r.get("game_meta") or {})
        if meta.get("avatar") != avatar:
            meta["avatar"] = avatar
            supabase.table("profiles").update({"game_meta": meta}).eq("id", r["id"]).execute()


def public_view(p: dict) -> dict:
    """A profile row as other players may see it."""
    return {
        "username": p.get("username"),
        "display_username": p.get("display_username") or p.get("username"),
        "game": p.get("game"),
        "platform": p.get("platform"),
        "region": p.get("region"),
        "country": profile_country(p),
        "city": p.get("city"),
        "avatar": profile_avatar(p),
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


def like_maps(user_id: str, game: str) -> tuple[dict[str, str], dict[str, str]]:
    """({who I liked: when}, {who liked me: when}) for one game, read with ONE query — a single SQL statement sees
    one consistent snapshot, so "mutual" (which unlocks contact info) can never be pieced together from two
    different moments (e.g. my like read before I took it back + their like read after they made it)."""
    rows = (
        supabase.table("likes").select("from_user_id,to_user_id,created_at").eq("game", game)
        .or_(f"from_user_id.eq.{user_id},to_user_id.eq.{user_id}").execute().data or []
    )
    i_liked, liked_me = {}, {}
    for r in rows:
        if str(r.get("from_user_id")) == user_id and r.get("to_user_id"):
            i_liked[str(r["to_user_id"])] = r.get("created_at")
        elif str(r.get("to_user_id")) == user_id and r.get("from_user_id"):
            liked_me[str(r["from_user_id"])] = r.get("created_at")
    return i_liked, liked_me


def mutual_ids(user_id: str, game: str, blocked: set[str] | None = None) -> list[str]:
    """Players who liked me back in this game (blocked players excluded)."""
    i_liked, liked_me = like_maps(user_id, game)
    mutual = [u for u in i_liked if u in liked_me]
    if not mutual:
        return []
    if blocked is None:
        blocked = get_blocked_ids(user_id)
    return [u for u in mutual if u not in blocked]


def is_unique_violation(e: Exception) -> bool:
    return "23505" in str(e) or "duplicate key" in str(e)


# The accounts table (db/migrations/001, applied 2026-10-18) is the one source of truth for usernames.
# Any error reading it is an error (503 from the handler below) — never a silent fallback to profile names.
def account_row(user_id: str) -> dict | None:
    res = supabase.table("accounts").select("username,display_username").eq("user_id", user_id).limit(1).execute()
    return res.data[0] if res.data else None


def user_id_for_username(username: str) -> str | None:
    u = (username or "").strip().lower()
    if not USERNAME_RE.match(u):
        return None
    res = supabase.table("accounts").select("user_id").eq("username", u).limit(1).execute()
    return str(res.data[0]["user_id"]) if res.data else None


def claim_username(user_id: str, username: str, display_username: str) -> tuple[str, str]:
    """Reserve a username for this account for good, and return the account's name as stored.
    If two first saves of the same user race, the first one wins and the second uses the winner's name
    (so profiles and accounts never disagree); a name owned by someone else is a 409."""
    try:
        supabase.table("accounts").insert(
            {"user_id": user_id, "username": username, "display_username": display_username}).execute()
        return username, display_username
    except Exception as e:
        if not is_unique_violation(e):
            raise
    mine = account_row(user_id)
    if mine:
        return mine["username"], mine.get("display_username") or mine["username"]
    raise HTTPException(status_code=409, detail="This PlayMate username is already taken.")


def auth_user(user_id: str):
    """The Supabase auth user, or None if it doesn't exist. An Auth outage raises 503 instead of looking
    like "no such user" (which could otherwise make us save default values over real ones)."""
    try:
        return supabase.auth.admin.get_user_by_id(user_id).user
    except AuthApiError as e:
        if getattr(e, "status", None) == 404 or getattr(e, "code", None) == "user_not_found":
            return None
        logger.warning("auth_user(%s) failed: %s", user_id, e)
        raise HTTPException(status_code=503, detail="Account service unavailable, please try again")
    except Exception as e:
        logger.warning("auth_user(%s) failed: %s", user_id, e)
        raise HTTPException(status_code=503, detail="Account service unavailable, please try again")


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
def optional_user_id(authorization: str | None = Header(default=None)) -> str | None:
    """The viewer's user_id when a valid token is sent, else None (public pages work without login)."""
    if not authorization:
        return None
    try:
        return get_current_user_id(authorization)
    except HTTPException:
        return None


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
        # Supabase user tokens: HS256 with the project secret, aud "authenticated", always exp + sub.
        # (The issuer isn't pinned: the secret is unique to this project already.)
        payload = jwt.decode(parts[1].strip(), SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated",
                             options={"require": ["exp", "sub"]})
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = str(payload.get("sub") or "")
    if not UUID_RE.match(user_id):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return user_id


# =========================================================
# pages
# =========================================================
def page(name: str) -> HTMLResponse:
    # no-cache: browsers must re-check the page, so a deploy's new ?v= asset links are picked up right away
    return HTMLResponse((BASE_DIR / name).read_text(encoding="utf-8"), headers={"Cache-Control": "no-cache"})


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
    """Profile page with the player's name in <title> and share previews (Discord/Telegram don't run JS)."""
    if username is None:
        return page("profile.html")   # /profile without a name: the page shows its own message
    uid = user_id_for_username(username)
    account = account_row(uid) if uid else None
    if not account:
        return HTMLResponse((BASE_DIR / "404.html").read_text(encoding="utf-8"), status_code=404,
                            headers={"Cache-Control": "no-cache"})
    rows = supabase.table("profiles").select("game").eq("user_id", uid).execute().data or []
    shown = account.get("display_username") or account["username"]
    games = ", ".join(GAMES[r["game"]]["name"] for r in rows if r.get("game") in GAMES)
    title = f"{shown} on PlayMate"
    desc = f"{shown} plays {games}. Find teammates by region, language and mic on PlayMate." if games \
        else f"{shown} is on PlayMate — find teammates by region, language and mic."
    url = f"{PUBLIC_URL}/u/{account['username']}"
    t, d, u = html.escape(title), html.escape(desc), html.escape(url)
    meta = (f'<title>{t}</title>\n  <meta name="description" content="{d}">\n'
            f'  <meta property="og:type" content="profile">\n  <meta property="og:title" content="{t}">\n'
            f'  <meta property="og:description" content="{d}">\n  <meta property="og:url" content="{u}">\n'
            f'  <meta property="og:image" content="{PUBLIC_URL}/static/img/og-image.png">\n'
            f'  <meta name="twitter:card" content="summary_large_image">')
    body = (BASE_DIR / "profile.html").read_text(encoding="utf-8").replace("<title>PlayMate | Player profile</title>", meta, 1)
    return HTMLResponse(body, headers={"Cache-Control": "no-cache"})


@app.get("/settings", response_class=HTMLResponse)
def settings_page():
    return page("settings.html")


@app.get("/terms", response_class=HTMLResponse)
@app.get("/privacy", response_class=HTMLResponse)
def legal_page():
    return page("legal.html")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /settings\nDisallow: /api/\n"


@app.exception_handler(StarletteHTTPException)
async def not_found_page(request, exc):
    # pages get a friendly 404 page; API calls keep their JSON errors
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/static/")):
        return HTMLResponse((BASE_DIR / "404.html").read_text(encoding="utf-8"), status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.get("/health")
def health(deep: bool = False):
    # deep=1 also touches the database (used by keep-alive pings so Supabase doesn't pause)
    if deep:
        supabase.table("profiles").select("id").limit(1).execute()
    return {"status": "ok"}


# =========================================================
# games / meta (public)
# =========================================================
def count_profiles(**filters) -> int:
    q = supabase.table("profiles").select("id", count="exact", head=True)
    for col, (op, val) in filters.items():
        q = getattr(q, op)(col, val)
    return q.execute().count or 0


_cache: dict[str, tuple[float, object]] = {}


_CACHE_MAX = 200


def cached(key: str, seconds: float, compute):
    """Tiny per-process cache for public numbers that don't need to be exact to the second.
    Keys only come from validated values (game ids, known regions) and the cache is capped."""
    hit = _cache.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < seconds:
        return hit[1]
    value = compute()
    if len(_cache) >= _CACHE_MAX:
        _cache.clear()
    _cache[key] = (now, value)
    return value


def forget_counts() -> None:
    """A profile was added/removed: drop cached counters so the next request recounts."""
    for k in [k for k in _cache if k == "player_counts" or k.startswith("stats:")]:
        _cache.pop(k, None)


def player_counts() -> dict[str, int]:
    """Profiles per game, as exact counts (a plain select would stop at the API's row limit), cached a minute."""
    return cached("player_counts", 60, lambda: {g: count_profiles(game=("eq", g)) for g in GAME_ORDER})


@app.get(f"{API_PREFIX}/games")
def list_games():
    counts = player_counts()
    return {"games": [{**game_summary(g), "players": counts.get(g, 0)} for g in GAME_ORDER]}


@app.get(f"{API_PREFIX}/meta/{{game}}")
def get_game_meta(game: str):
    return game_meta(norm_game(game))


@app.get(f"{API_PREFIX}/stats")
def stats(game: str = DEFAULT_GAME, region: str | None = None):
    """Small 'the site is alive' numbers for empty states."""
    game = norm_game(game)
    if region not in {r["id"] for r in REGIONS}:
        region = None   # unknown values don't reach the DB or the cache

    def compute():
        now_iso = now_utc().isoformat()
        day_ago = (now_utc() - timedelta(days=1)).isoformat()
        return {
            "game": game,
            "players": player_counts().get(game, 0),
            "in_region": count_profiles(game=("eq", game), region=("eq", region)) if region else 0,
            "looking_now": count_profiles(game=("eq", game), looking_until=("gt", now_iso)),
            "active_today": count_profiles(game=("eq", game), last_active=("gt", day_ago)),
        }
    return cached(f"stats:{game}:{region or ''}", 20, compute)


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
    country: str | None = None
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

    # username: locked once chosen (same name in every game, kept even if every game is removed)
    existing = my_profile_row(user_id, game, "username,display_username,game_meta")
    if not existing:
        any_game = supabase.table("profiles").select("username,display_username,game_meta").eq("user_id", user_id).limit(1).execute()
        existing = any_game.data[0] if any_game.data else None
    account = account_row(user_id)
    needs_claim = False
    if account:
        username, display_username, locked = account["username"], account.get("display_username") or account["username"], True
    elif existing:
        username = (existing.get("username") or "").strip().lower()
        display_username = existing.get("display_username") or username
        locked = True
        needs_claim = True   # an older player without an accounts row yet
    else:
        raw = (profile.username or "").strip()
        if not USERNAME_RE.match(raw):
            raise HTTPException(status_code=422, detail="Username must be 3-24 characters: letters, numbers, _ . -")
        taken = supabase.table("profiles").select("user_id").eq("username", raw.lower()).neq("user_id", user_id).limit(1).execute()
        owner = user_id_for_username(raw)
        if taken.data or (owner and owner != user_id):
            raise HTTPException(status_code=409, detail="This PlayMate username is already taken.")
        username, display_username, locked = raw.lower(), raw, False
        needs_claim = True

    # common fields
    missing = []
    region = (profile.region or "").strip()
    region_def = next((r for r in REGIONS if r["id"] == region), None)
    if not region_def:
        missing.append("Region")
    mic = (profile.mic or "").strip()
    if mic not in ("voice", "both", "none"):
        missing.append("Mic")
    allowed_langs = {lang["code"] for lang in LANGUAGES}
    languages = ",".join(dict.fromkeys(c for c in parse_languages(profile.languages) if c in allowed_langs))
    if not languages:
        missing.append("Languages")
    country_def = get_country(region, (profile.country or "").strip())
    if region_def and not country_def:
        missing.append("Country")
    city = (profile.city or "").strip() or None
    if city and (not country_def or city not in country_def["cities"]):
        city = None
    platform = (profile.platform or "").strip() or None
    if platform not in g["platforms"]:
        platform = g["platforms"][0] if len(g["platforms"]) == 1 else None
    if not platform:
        missing.append("Platform")   # crossplay filters depend on it

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
        "city": city,
        "mic": mic,
        "languages": languages,
        "game_meta": {
            "fields": fields,
            "country": country_def["name"] if country_def else None,
            "avatar": current_avatar(user_id, existing),
        },
    }
    for f in g["fields"]:
        if f.get("column"):
            payload[f["column"]] = fields.get(f["id"])

    if needs_claim:
        username, display_username = claim_username(user_id, username, display_username)
        payload["username"], payload["display_username"] = username, display_username
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
    forget_counts()
    return {"status": "saved", "locked_username": locked, "data": saved}


@app.delete(f"{API_PREFIX}/profile")
def delete_game_profile(game: str, user_id: str = Depends(get_current_user_id)):
    """Remove one game from my profile (my likes in that game go too)."""
    game = norm_game(game)
    supabase.table("likes").delete().eq("from_user_id", user_id).eq("game", game).execute()
    supabase.table("likes").delete().eq("to_user_id", user_id).eq("game", game).execute()
    supabase.table("profiles").delete().eq("user_id", user_id).eq("game", game).execute()
    forget_counts()
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
    account = account_row(user_id)
    return {
        "username": account["username"] if account else (rows[0]["username"] if rows else None),
        "display_username": account["display_username"] if account else (rows[0].get("display_username") if rows else None),
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
    exclude: list[str] | None = None   # usernames the player skipped this session ("Show more" pages past them)


FLEX_VALUES = {"Fill", "Any"}


def score_pair(me: dict, other: dict, game: str) -> tuple[int, list[str]]:
    g = GAMES[game]
    score, reasons = 0, []

    if me.get("region") and other.get("region") == me.get("region"):
        score += 35
        reasons.append(f"Same region: {region_label(me['region'])}")
        my_country = profile_country(me)
        if my_country and profile_country(other) == my_country:
            score += 5
            reasons.append(f"Same country: {my_country}")
        if me.get("city") and other.get("city") == me.get("city"):
            score += 5
            reasons.append(f"Same city: {me['city']}")

    langs = sorted(set(parse_languages(me.get("languages"))) & set(parse_languages(other.get("languages"))))
    if langs:
        score += 15 + min(5, 5 * (len(langs) - 1))
        reasons.append("Speaks " + ", ".join(LANGUAGE_LABELS.get(l, l) for l in langs))

    if (me.get("mic") or "") in VOICE and (other.get("mic") or "") in VOICE:
        score += 10
        reasons.append("Both use voice chat")

    if len(g["platforms"]) > 1 and me.get("platform") and other.get("platform") == me.get("platform"):
        score += 5
        reasons.append(f"Same platform: {me['platform']}")

    mine, theirs = profile_fields(me), profile_fields(other)
    for f in g["fields"]:
        v, w = mine.get(f["id"]), theirs.get(f["id"])
        if not v or not w:
            continue
        if f.get("match") == "diff":
            # roles/positions: a squad wants different ones ("Fill"/"Any" fits with everyone)
            if v != w or v in FLEX_VALUES:
                score += f["weight"]
                reasons.append(f"Complementary {f['label'].lower()}: you {v}, them {w}")
        elif v == w:
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
    skipped = {str(u).strip().lower() for u in (req.exclude or [])[:1000] if u}
    likes_me = {
        str(r["from_user_id"]) for r in
        (supabase.table("likes").select("from_user_id").eq("to_user_id", user_id).eq("game", game).execute().data or [])
    }

    near = (
        supabase.table("profiles").select("*").eq("game", game).eq("region", me.get("region") or "")
        .order("last_active", desc=True, nullsfirst=False).limit(500).execute().data or []
    )
    far = (
        supabase.table("profiles").select("*").eq("game", game).neq("region", me.get("region") or "")
        .order("last_active", desc=True, nullsfirst=False).limit(300).execute().data or []
    )
    players = near + far
    my_fields = profile_fields(me)
    matches = []
    for p in players:
        if not p.get("user_id") or str(p["user_id"]) in hidden:
            continue
        if (p.get("username") or "").lower() in skipped:
            continue
        # no crossplay between our platforms / different Minecraft edition / different LoL server
        if not can_play_together(game, me.get("platform"), p.get("platform"), my_fields, profile_fields(p)):
            continue
        if req.same_language_only and not (my_langs & set(parse_languages(p.get("languages")))):
            continue
        view = public_view(p)
        if req.looking_only and not view["looking_now"]:
            continue
        score, reasons = score_pair(me, p, game)
        likes_you = str(p["user_id"]) in likes_me
        if likes_you:
            reasons.insert(0, "Already likes you — like back to match")
        if view["looking_now"]:
            reasons.insert(0, "Looking for a squad right now")
        matches.append({
            "username": p.get("username"),
            "match_percent": score,
            "reasons": reasons,
            "looking_now": view["looking_now"],
            "likes_you": likes_you,
            "profile": view,
        })

    # players looking right now first, then people who already like me, then by score
    matches.sort(key=lambda m: (m["looking_now"], m["likes_you"], m["match_percent"]), reverse=True)
    return {"target_user": me.get("username"), "game": game, "total": len(matches), "has_more": len(matches) > 20,
            "matches": matches[:20]}


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

    me = require_profile(user_id, game)
    from_user = (me.get("username") or "").strip().lower()
    if from_user == to_user:
        raise HTTPException(status_code=400, detail="You cannot like yourself")

    target = supabase.table("profiles").select("*").eq("username", to_user).eq("game", game).limit(1).execute()
    if not target.data or not target.data[0].get("user_id"):
        raise HTTPException(status_code=404, detail="Target user not found")
    to_user_id = str(target.data[0]["user_id"])
    if to_user_id in get_blocked_ids(user_id):
        raise HTTPException(status_code=403, detail="You can't like this player")
    if not compatible(game, me, target.data[0]):
        raise HTTPException(status_code=409, detail="You can't play together: different platform, edition or server.")

    payload = {"from_user": from_user, "to_user": to_user, "from_user_id": user_id, "to_user_id": to_user_id, "game": game}
    exists = (
        supabase.table("likes").select("id")
        .eq("from_user_id", user_id).eq("to_user_id", to_user_id).eq("game", game).limit(1).execute()
    )
    already = bool(exists.data)
    if not already:
        try:
            supabase.table("likes").insert(payload).execute()
        except Exception as e:
            if "duplicate key" not in str(e):   # a double click that raced us is fine
                raise
            already = True
    # checked after our like is stored, so two people liking each other at the same moment both see "mutual"
    reverse = (
        supabase.table("likes").select("id")
        .eq("from_user_id", to_user_id).eq("to_user_id", user_id).eq("game", game).limit(1).execute()
    )
    mutual = bool(reverse.data)
    status = "already_exists" if already else ("mutual" if mutual else "liked")
    return {"status": status, "mutual": mutual, "data": payload}


@app.delete(f"{API_PREFIX}/like")
def unmatch(to_user: str, game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    """Unmatch / take back a like in one game: removes the likes in both directions between us."""
    game = norm_game(game)
    other = supabase.table("profiles").select("user_id").eq("username", (to_user or "").strip().lower()).eq("game", game).limit(1).execute()
    if not other.data:
        raise HTTPException(status_code=404, detail="Player not found")
    other_id = str(other.data[0]["user_id"])
    supabase.table("likes").delete().eq("from_user_id", user_id).eq("to_user_id", other_id).eq("game", game).execute()
    supabase.table("likes").delete().eq("from_user_id", other_id).eq("to_user_id", user_id).eq("game", game).execute()
    return {"status": "unmatched", "game": game}


def compatible(game: str, a: dict, b: dict) -> bool:
    return can_play_together(game, a.get("platform"), b.get("platform"), profile_fields(a), profile_fields(b))


def social_state(user_id: str, game: str, me: dict | None = None) -> dict:
    """Squad, pending likes and "liked you" for one game, from 3 queries: all likes involving me (ONE consistent
    read, see like_maps), blocks, and one profiles lookup for everyone involved."""
    i_liked, liked_me = like_maps(user_id, game)
    blocked = get_blocked_ids(user_id) if (i_liked or liked_me) else set()
    mutual = {u for u in i_liked if u in liked_me and u not in blocked}
    pending = {u for u in i_liked if u not in liked_me and u not in blocked}
    incoming = {u for u in liked_me if u not in i_liked and u not in blocked}
    everyone = mutual | pending | incoming
    rows = supabase.table("profiles").select("*").eq("game", game).in_("user_id", list(everyone)).execute().data or [] if everyone else []
    if me is None:
        me = my_profile_row(user_id, game)

    squad, waiting, liked_you = [], [], []
    for p in rows:
        uid = str(p["user_id"])
        v = public_view(p)
        if uid in mutual:
            # mutual squadmates may see how to reach each other
            v["in_game_username"] = p.get("in_game_username")
            v["discord_username"] = p.get("discord_username")
            squad.append(v)
        elif uid in pending:
            waiting.append({"username": v["username"], "display_username": v["display_username"], "region": v["region"],
                            "avatar": v["avatar"], "last_active": v["last_active"], "liked_at": i_liked.get(uid)})
        elif uid in incoming:
            if me and not compatible(game, me, p):
                continue   # they changed platform/edition/server since: you couldn't play together
            v["liked_at"] = liked_me.get(uid)
            liked_you.append(v)
    waiting.sort(key=lambda x: x.get("liked_at") or "", reverse=True)
    liked_you.sort(key=lambda x: x.get("liked_at") or "", reverse=True)
    return {"squadmates": squad, "pending": waiting, "incoming": liked_you}


@app.get(f"{API_PREFIX}/poll")
def poll(game: str = DEFAULT_GAME, ping: bool = False, user_id: str = Depends(get_current_user_id)):
    """Everything the app refreshes every few seconds, in one request: marks me active (ping=1),
    and returns my squad (with contacts), my pending likes and who liked me."""
    game = norm_game(game)
    me = require_profile(user_id, game)
    if ping:
        supabase.table("profiles").update({"last_active": now_utc().isoformat()}).eq("user_id", user_id).eq("game", game).execute()
    return {"username": me.get("username"), "game": game, **social_state(user_id, game, me)}


@app.get(f"{API_PREFIX}/incoming-likes")
def incoming_likes(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    """People who liked me in this game and I haven't answered yet (no contact info: not mutual)."""
    game = norm_game(game)
    me = require_profile(user_id, game)
    return {"game": game, "incoming": social_state(user_id, game, me)["incoming"]}


@app.get(f"{API_PREFIX}/my-squad-details")
def my_squad_details(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    game = norm_game(game)
    me = require_profile(user_id, game, "username")
    return {"username": me.get("username"), "game": game, "squadmates": social_state(user_id, game)["squadmates"]}


@app.get(f"{API_PREFIX}/pending-likes")
def pending_likes(game: str = DEFAULT_GAME, user_id: str = Depends(get_current_user_id)):
    """People I liked who haven't liked me back yet (no in-game name: not mutual)."""
    game = norm_game(game)
    return {"game": game, "pending": social_state(user_id, game)["pending"]}


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
    key = {"blocker_id": user_id, "blocked_id": blocked_id, "game": game}
    if req.report:
        # sets reported=true (and the reason, if given) on the row; never writes reported=false
        row = {**key, "reported": True}
        reason = (req.reason or "").strip()[:300]
        if reason:
            row["reason"] = reason
        supabase.table("blocks").upsert(row, on_conflict="blocker_id,blocked_id,game").execute()
    else:
        # a plain block only creates the row; an existing row (and any report on it) is left untouched
        supabase.table("blocks").upsert({**key, "reported": False}, on_conflict="blocker_id,blocked_id,game",
                                        ignore_duplicates=True).execute()
    now = supabase.table("blocks").select("reported").eq("blocker_id", user_id).eq("blocked_id", blocked_id).eq("game", game).execute().data or []
    return {"status": "blocked", "reported": any(r.get("reported") for r in now)}


@app.get(f"{API_PREFIX}/blocks")
def my_blocks(user_id: str = Depends(get_current_user_id)):
    """Players I blocked (one entry per player, whatever game the block was made in)."""
    rows = supabase.table("blocks").select("blocked_id,reported,created_at").eq("blocker_id", user_id).execute().data or []
    by_user = {}
    for r in rows:
        b = by_user.setdefault(str(r["blocked_id"]), {"reported": False, "blocked_at": r.get("created_at")})
        b["reported"] = b["reported"] or bool(r.get("reported"))
    if not by_user:
        return {"blocked": []}
    ids = list(by_user)
    accounts = {str(a["user_id"]): a for a in
                supabase.table("accounts").select("user_id,username,display_username").in_("user_id", ids).execute().data or []}
    avatars = {}
    for p in supabase.table("profiles").select("user_id,game_meta").in_("user_id", ids).execute().data or []:
        avatars.setdefault(str(p["user_id"]), profile_avatar(p))
    out = []
    for uid, b in by_user.items():
        a = accounts.get(uid)
        if not a:
            continue   # that player deleted their account
        out.append({"username": a["username"], "display_username": a.get("display_username") or a["username"],
                    "avatar": avatars.get(uid, ""), "reported": b["reported"], "blocked_at": b["blocked_at"]})
    out.sort(key=lambda x: x.get("blocked_at") or "", reverse=True)
    return {"blocked": out}


@app.delete(f"{API_PREFIX}/block")
def unblock(to_user: str, user_id: str = Depends(get_current_user_id)):
    """Unblock a player everywhere. Players you reported stay blocked (the report must stay on record)."""
    other_id = user_id_for_username(to_user)
    if not other_id:
        raise HTTPException(status_code=404, detail="Player not found")
    # only plain blocks are removed (a report arriving at the same moment can't be deleted by this)
    supabase.table("blocks").delete().eq("blocker_id", user_id).eq("blocked_id", other_id).eq("reported", False).execute()
    left = supabase.table("blocks").select("id").eq("blocker_id", user_id).eq("blocked_id", other_id).execute().data or []
    if left:
        raise HTTPException(status_code=409, detail="You reported this player, so they stay blocked.")
    return {"status": "unblocked"}


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
    account = account_row(user_id)
    username = account["username"] if account else (games[0]["username"] if games else None)
    blocked = get_blocked_ids(user_id)
    mutual_count = sum(len(mutual_ids(user_id, r["game"], blocked)) for r in games)
    referrals = int(((getattr(user, "app_metadata", None) or {}).get("playmate") or {}).get("referral_count") or 0)
    return {
        **account_data(user),
        "username": username,
        "display_username": (account or {}).get("display_username") or (games[0].get("display_username") if games else None),
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
        if "avatar" in changes:
            sync_profile_avatar(user_id, changes["avatar"])
    return my_account_payload(user_id)


class DeleteAccountRequest(BaseModel):
    confirm: str


@app.delete(f"{API_PREFIX}/account")
def delete_account(req: DeleteAccountRequest, user_id: str = Depends(get_current_user_id)):
    """Permanently delete my account: every game profile, my likes (sent and received), blocks/reports that
    involve me, and the login itself. The client must send confirm="DELETE"."""
    if (req.confirm or "").strip().upper() != "DELETE":
        raise HTTPException(status_code=422, detail='Type DELETE to confirm')
    supabase.table("likes").delete().eq("from_user_id", user_id).execute()
    supabase.table("likes").delete().eq("to_user_id", user_id).execute()
    supabase.table("blocks").delete().eq("blocker_id", user_id).execute()
    supabase.table("blocks").delete().eq("blocked_id", user_id).execute()
    supabase.table("profiles").delete().eq("user_id", user_id).execute()
    supabase.table("accounts").delete().eq("user_id", user_id).execute()
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception:
        logger.exception("delete_account: auth user %s could not be deleted", user_id)
        raise HTTPException(status_code=500, detail="Your PlayMate data was removed, but the login could not be deleted. Please contact support.")
    return {"status": "deleted"}


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
    created = parse_ts(getattr(user, "created_at", None))
    if not created or now_utc() - created > timedelta(days=3):
        return {"status": "ignored"}
    ref_id = user_id_for_username(ref)
    if not ref_id or ref_id == user_id:
        return {"status": "ignored"}
    save_account_meta(user, {"referred_by": ref})
    # keep a counter on the inviter (no need to scan every user to count invites)
    inviter = auth_user(ref_id)
    if inviter:
        count = int(((inviter.app_metadata or {}).get("playmate") or {}).get("referral_count") or 0)
        save_account_meta(inviter, {"referral_count": count + 1})
    return {"status": "saved"}


# =========================================================
# public profile page data (no in-game names / discord)
# =========================================================
@app.get(f"{API_PREFIX}/public-profile")
def public_profile(username: str, viewer_id: str | None = Depends(optional_user_id)):
    uid = user_id_for_username(username)
    if not uid:
        raise HTTPException(status_code=404, detail="Player not found")
    if viewer_id and viewer_id != uid and viewer_id in get_blocked_ids(uid):
        raise HTTPException(status_code=404, detail="Player not found")   # blocked either way
    user = auth_user(uid)
    names = account_row(uid) or {}
    rows = supabase.table("profiles").select(PUBLIC_PROFILE_FIELDS).eq("user_id", uid).execute().data or []
    blocked = get_blocked_ids(uid)
    mutual_count = sum(len(mutual_ids(uid, r["game"], blocked)) for r in rows)
    acc = account_data(user) if user else account_data(None)
    last_active = max((r.get("last_active") or "" for r in rows), default="") or None
    return {
        "username": names.get("username") or username.lower(),
        "display_username": names.get("display_username") or names.get("username") or username,
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
