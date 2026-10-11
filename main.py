from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from pydantic import BaseModel
from pathlib import Path
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions
from dotenv import load_dotenv
from fastapi import Header, Depends, Request, Query
from jwt import PyJWTError

import httpx
import jwt
import os
import re


# لود کردن .env از کنار همین فایل
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # از Supabase Project Settings بگیر
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

app = FastAPI()
API_PREFIX = "/api"


# ----------------- مدل پروفایل -----------------
class GamerProfile(BaseModel):
    username: str                      # PlayMate username
    game: str | None = "battlefield"   # per-game profile
    in_game_username: str | None = None  # hidden until mutual
    discord_username: str | None = None  # hidden until mutual
    platform: str | None = None
    region: str
    city: str | None = None
    favorite_mode: str
    class_type: str
    mic: str
    languages: str
    profile_pic_url: str | None = None
    wallpaper_url: str | None = None
    game_meta: dict | None = None      # JSON for future

# ----------------- اضاقه کردن وضعیت آنلاین -----------------

from datetime import datetime, timedelta, timezone

def touch_last_active(username: str, game: str = "battlefield") -> str | None:
    u = (username or "").strip().lower()
    g = (game or "battlefield").strip().lower()
    if not u:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    supabase.table("profiles").update({"last_active": now_iso}).eq("username", u).eq("game", g).execute()
    return now_iso

def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    """
    Reads Supabase access token from Authorization header and returns user_id (sub).
    Raises 401 if missing/invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server missing SUPABASE_JWT_SECRET")

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},  # ساده نگه می‌داریم
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing sub")
        return str(user_id)
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/api/ping")
def ping(game: str = "battlefield", user_id: str = Depends(get_current_user_id)):
    game = (game or "battlefield").strip().lower()

    # find username for this user_id + game
    me = (
    supabase.table("profiles")
    .select("username,display_username")
    .eq("user_id", user_id)
    .eq("game", game)
    .limit(1)
    .execute()
    )
    if not me.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")

    username = (me.data[0].get("username") or "").strip().lower()
    display_username = (me.data[0].get("display_username") or me.data[0].get("username") or "").strip()

    last_active = touch_last_active(username, game)
    return {
    "status": "ok",
    "user_id": user_id,
    "username": username,
    "display_username": display_username,
    "game": game,
    "last_active": last_active,
    }




# ----------------- توابع کمکی -----------------
REQUIRED_PROFILE_FIELDS = ("region", "favorite_mode", "class_type", "mic", "languages")

def require_profile_fields(profile: "GamerProfile") -> None:
    missing = [f for f in REQUIRED_PROFILE_FIELDS if not (getattr(profile, f, None) or "").strip()]
    if missing:
        raise HTTPException(status_code=422, detail="Missing required fields: " + ", ".join(missing))

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,24}$")
FREE_TEXT_RE = re.compile(r"^[^<>\"'`]{1,40}$")  # IGN / Discord: no HTML-ish characters


def clean_optional_text(value: str | None, field: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    if not FREE_TEXT_RE.match(v):
        raise HTTPException(status_code=422, detail=f"{field} must be 1-40 characters and cannot contain < > \" ' `")
    return v


def get_blocked_ids(user_id: str, game: str) -> set[str]:
    """Users I blocked + users who blocked me (hidden from each other everywhere)."""
    res = (
        supabase.table("blocks")
        .select("blocker_id,blocked_id")
        .eq("game", game)
        .or_(f"blocker_id.eq.{user_id},blocked_id.eq.{user_id}")
        .execute()
    )
    out: set[str] = set()
    for r in res.data or []:
        other = r["blocked_id"] if str(r["blocker_id"]) == user_id else r["blocker_id"]
        out.add(str(other))
    return out


def is_looking_now(looking_until: str | None) -> bool:
    if not looking_until:
        return False
    try:
        return datetime.fromisoformat(str(looking_until).replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except ValueError:
        return False


def parse_languages(lang_str: str) -> list[str]:
    if not lang_str:
        return []
    return [x.strip().lower() for x in lang_str.split(",") if x.strip()]




# ----------------- روت‌ها -----------------
@app.get("/", response_class=HTMLResponse)
def landing_page():
    html_path = Path(__file__).parent / "landing.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))

@app.get("/bf", response_class=HTMLResponse)
def bf_page():
    html_path = Path(__file__).parent / "ui.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))

@app.get("/ui")
def ui_redirect():
    return RedirectResponse(url="/bf", status_code=302)

@app.get("/profile", response_class=HTMLResponse)
def profile_page():
    # این فایل را در کنار ui.html قرار می‌دهیم
    path = os.path.join(os.path.dirname(__file__), "profile.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/profile-full")
def profile_full(username: str):
    username = (username or "").strip().lower()

    PUBLIC_PROFILE_FIELDS = (
        "username,display_username,game,platform,region,city,languages,mic,"
        "favorite_mode,class_type,profile_pic_url,wallpaper_url,game_meta,created_at,last_active"
    )

    result = (
        supabase
        .table("profiles")
        .select(PUBLIC_PROFILE_FIELDS)
        .eq("username", username)
        .execute()
    )

    if not result.data:
        return {"error": "user not found"}

    return result.data[0]



@app.get("/health")
def health(deep: bool = False):
    # deep=1 also touches the database (used by the keep-alive job so Supabase doesn't pause)
    if deep:
        supabase.table("profiles").select("id").limit(1).execute()
    return {"status": "ok"}


@app.post("/api/profile")
def create_profile(profile: GamerProfile, user_id: str = Depends(get_current_user_id)):
    require_profile_fields(profile)
    game = (profile.game or "battlefield").strip().lower()

    # 1) اگر قبلاً برای این user_id + game پروفایل وجود دارد:
    #    username را از DB بگیر و body را نادیده بگیر (LOCK)
    existing = (
        supabase.table("profiles")
        .select("username, display_username")
        .eq("user_id", user_id)
        .eq("game", game)
        .limit(1)
        .execute()
    )

    if existing.data:
        username = (existing.data[0].get("username") or "").strip().lower()
        display_username = (
            existing.data[0].get("display_username")
            or existing.data[0].get("username")
            or username
        )
        locked_username = True
    else:
        raw_username = (profile.username or "").strip()
        if not raw_username:
            raise HTTPException(status_code=400, detail="username is required")
        if not USERNAME_RE.match(raw_username):
            raise HTTPException(
                status_code=422,
                detail="Username must be 3-24 characters: letters, numbers, _ . -"
            )
        username = raw_username.lower()
        display_username = raw_username
        locked_username = False

    # 2) sanitize in_game_username / discord_username
    in_game_username = clean_optional_text(profile.in_game_username, "In-game username")
    discord_username = clean_optional_text(profile.discord_username, "Discord username")

    payload = {
        "user_id": user_id,
        "username": username,
        "display_username": display_username,
        "game": game,

        "in_game_username": in_game_username,
        "discord_username": discord_username,
        "platform": profile.platform,
        "region": profile.region,
        "city": profile.city,
        "favorite_mode": profile.favorite_mode,
        "class_type": profile.class_type,
        "mic": profile.mic,
        "languages": profile.languages,
        "profile_pic_url": profile.profile_pic_url,
        "wallpaper_url": profile.wallpaper_url,
        "game_meta": profile.game_meta or {},
    }

    try:
        result = (
            supabase
            .table("profiles")
            .upsert(payload, on_conflict="user_id,game")
            .execute()
        )
    except Exception as e:
        msg = str(e)
        if ("profiles_game_ign_unique" in msg) or ("duplicate key value violates unique constraint" in msg):
            raise HTTPException(
                status_code=409,
                detail="This Battlefield username is already used by another PlayMate user. Please choose a different one."
            )
        raise

    if getattr(result, "error", None):
        raise HTTPException(status_code=500, detail="Profile save failed.")

    # اگر result.data خالی بود، حداقل payload را بده
    saved = (result.data[0] if (result.data and len(result.data) > 0) else payload)

    return {"status": "saved", "locked_username": locked_username, "data": saved}



PUBLIC_PROFILE_FIELDS = (
    "username,display_username,game,platform,region,city,languages,mic,"
    "favorite_mode,class_type,profile_pic_url,wallpaper_url,game_meta,created_at,last_active"
)

@app.get(f"{API_PREFIX}/my-profile")
def my_profile(game: str = "battlefield", user_id: str = Depends(get_current_user_id)):
    """The logged-in user's own profile (incl. in_game_username), so any device can restore the form."""
    game = (game or "battlefield").strip().lower()
    result = (
        supabase.table("profiles")
        .select(PUBLIC_PROFILE_FIELDS + ",in_game_username,discord_username,looking_until")
        .eq("user_id", user_id)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")
    return result.data[0]

# Fields of another player that are safe to show in match results (no in_game_username)
MATCH_PUBLIC_FIELDS = (
    "username", "display_username", "game", "platform", "region", "city",
    "languages", "mic", "favorite_mode", "class_type", "profile_pic_url", "wallpaper_url",
)

@app.post("/api/match")
def match_players(current: GamerProfile, user_id: str = Depends(get_current_user_id)):
    require_profile_fields(current)

    game = (current.game or "battlefield").lower().strip()

    result = (
        supabase
        .table("profiles")
        .select("*")
        .eq("game", game)
        .execute()
    )
    players = [p for p in (result.data or []) if p.get("user_id")]


    current_langs = parse_languages(current.languages)
    voice_set = {"voice", "both"}

    matches = []

    # Derive "me" from auth token, not from request body (prevents spoof)
    me = (
        supabase.table("profiles")
        .select("username")
        .eq("user_id", user_id)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not me.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")

    current_username = (me.data[0].get("username") or "").strip().lower()

    # Players I already liked are not shown again (prevents re-show / re-like)
    liked_res = (
        supabase.table("likes")
        .select("to_user_id")
        .eq("from_user_id", user_id)
        .eq("game", game)
        .execute()
    )
    liked_ids = {str(r["to_user_id"]) for r in (liked_res.data or []) if r.get("to_user_id")}
    hidden_ids = liked_ids | get_blocked_ids(user_id, game)

    for p in players:
        if (p.get("username") or "").strip().lower() == current_username:
            continue
        if str(p.get("user_id")) in hidden_ids:
            continue

        score = 0
        reasons: list[str] = []

        if p.get("region") == current.region:
            score += 40
            reasons.append(f"Region match: {region_label(current.region)}")

        if p.get("favorite_mode") == current.favorite_mode:
            score += 25
            reasons.append(f"Same favorite mode: {current.favorite_mode}")

        if p.get("class_type") == current.class_type:
            score += 15
            reasons.append(f"Same class: {current.class_type}")

        other_langs = parse_languages(p.get("languages", ""))
        common_langs = sorted(set(current_langs) & set(other_langs))
        if common_langs:
            score += 10
            reasons.append("Common languages: " + ", ".join(common_langs))

        mic_current = (current.mic or "").lower()
        mic_other = (p.get("mic") or "").lower()
        if mic_current in voice_set and mic_other in voice_set:
            score += 10
            reasons.append("Both can use voice chat")

        if score > 100:
            score = 100

        safe_profile = {k: p.get(k) for k in MATCH_PUBLIC_FIELDS}
        looking = is_looking_now(p.get("looking_until"))
        if looking:
            reasons.insert(0, "Looking for a squad right now")

        matches.append({
            "username": p.get("username"),
            "match_percent": score,
            "reasons": reasons,
            "looking_now": looking,
            "profile": safe_profile,
        })

    # players looking right now first, then by score
    matches.sort(key=lambda x: (x["looking_now"], x["match_percent"]), reverse=True)

    return {
        "target_user": current_username,
        "game": game,
        "matches": matches[:10],
    }


@app.get("/api/my-squad-details")
def my_squad_details(
    game: str = "battlefield",
    user_id: str = Depends(get_current_user_id),
):
    game = (game or "battlefield").strip().lower()

    # derive "me" from auth token
    me = (
        supabase.table("profiles")
        .select("username, display_username")
        .eq("user_id", user_id)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not me.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")

    my_username = (me.data[0].get("username") or "").strip().lower()

    # touch last_active for ME only (no spoof)
    touch_last_active(my_username, game)

    # mutual via user_id
    out_res = (
        supabase.table("likes")
        .select("to_user_id")
        .eq("from_user_id", user_id)
        .eq("game", game)
        .execute()
    )
    outgoing_ids = [r.get("to_user_id") for r in (out_res.data or []) if r.get("to_user_id")]

    if not outgoing_ids:
        return {"username": my_username, "game": game, "squadmates": []}

    in_res = (
        supabase.table("likes")
        .select("from_user_id")
        .eq("to_user_id", user_id)
        .eq("game", game)
        .in_("from_user_id", outgoing_ids)
        .execute()
    )
    blocked = get_blocked_ids(user_id, game)
    mates_ids = [
        r.get("from_user_id") for r in (in_res.data or [])
        if r.get("from_user_id") and str(r.get("from_user_id")) not in blocked
    ]

    if not mates_ids:
        return {"username": my_username, "game": game, "squadmates": []}

    prof = (
        supabase.table("profiles")
        .select(
            "username,display_username,in_game_username,discord_username,profile_pic_url,wallpaper_url,"
            "region,city,languages,mic,favorite_mode,class_type,last_active,looking_until"
        )
        .eq("game", game)
        .in_("user_id", mates_ids)
        .execute()
    )
    mates = prof.data or []
    for m in mates:
        m["looking_now"] = is_looking_now(m.pop("looking_until", None))

    return {"username": my_username, "game": game, "squadmates": mates}


@app.get(f"{API_PREFIX}/pending-likes")
def pending_likes(game: str = "battlefield", user_id: str = Depends(get_current_user_id)):
    """People I liked who haven't liked me back yet (no in_game_username: not mutual)."""
    game = (game or "battlefield").strip().lower()

    out_res = (
        supabase.table("likes")
        .select("to_user_id, created_at")
        .eq("from_user_id", user_id)
        .eq("game", game)
        .execute()
    )
    liked_at = {str(r["to_user_id"]): r.get("created_at") for r in (out_res.data or []) if r.get("to_user_id")}
    if not liked_at:
        return {"game": game, "pending": []}

    in_res = (
        supabase.table("likes")
        .select("from_user_id")
        .eq("to_user_id", user_id)
        .eq("game", game)
        .in_("from_user_id", list(liked_at))
        .execute()
    )
    mutual_ids = {str(r["from_user_id"]) for r in (in_res.data or []) if r.get("from_user_id")}
    blocked = get_blocked_ids(user_id, game)
    pending_ids = [uid for uid in liked_at if uid not in mutual_ids and uid not in blocked]
    if not pending_ids:
        return {"game": game, "pending": []}

    prof = (
        supabase.table("profiles")
        .select("user_id,username,display_username,region,favorite_mode,class_type,last_active")
        .eq("game", game)
        .in_("user_id", pending_ids)
        .execute()
    )
    pending = []
    for p in prof.data or []:
        uid = str(p.pop("user_id"))
        pending.append({**p, "liked_at": liked_at.get(uid)})
    pending.sort(key=lambda x: x.get("liked_at") or "", reverse=True)

    return {"game": game, "pending": pending}


# ----------------- Public: profile squad (mutual) -----------------
@app.get("/profile-squad")
def profile_squad(username: str = Query(...), game: str = "battlefield"):
    username = (username or "").strip().lower()
    game = (game or "battlefield").strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="username is required")

    # 0) map username -> user_id (per-game)
    me = (
        supabase.table("profiles")
        .select("user_id, username")
        .eq("username", username)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not me.data:
        return {"username": username, "game": game, "squadmates": []}

    my_user_id = me.data[0].get("user_id")
    if not my_user_id:
        return {"username": username, "game": game, "squadmates": []}

    # 1) outgoing likes from me (by user_id)
    out_res = (
        supabase.table("likes")
        .select("to_user_id")
        .eq("from_user_id", my_user_id)
        .eq("game", game)
        .execute()
    )
    outgoing_ids = [r.get("to_user_id") for r in (out_res.data or []) if r.get("to_user_id")]
    if not outgoing_ids:
        return {"username": username, "game": game, "squadmates": []}

    # 2) incoming likes from those ids back to me => mutual
    in_res = (
        supabase.table("likes")
        .select("from_user_id")
        .eq("to_user_id", my_user_id)
        .eq("game", game)
        .in_("from_user_id", outgoing_ids)
        .execute()
    )
    mates_ids = [r.get("from_user_id") for r in (in_res.data or []) if r.get("from_user_id")]
    if not mates_ids:
        return {"username": username, "game": game, "squadmates": []}

    prof = (
        supabase.table("profiles")
        .select(
            # public endpoint: never expose in_game_username here
            "username,display_username,profile_pic_url,wallpaper_url,"
            "region,city,languages,mic,favorite_mode,class_type,last_active"
        )
        .eq("game", game)
        .in_("user_id", mates_ids)
        .execute()
    )

    return {"username": username, "game": game, "squadmates": prof.data or []}



# ----------------- مدل لایک / افزودن اسکادمیت -----------------
class LikeRequest(BaseModel):
    from_user: str | None = None   # legacy (optional)
    to_user: str
    game: str | None = "battlefield"


@app.post("/api/like")
def add_like(like: LikeRequest, user_id: str = Depends(get_current_user_id)):
        # from_user identity comes from Auth token (user_id)
    to_user = (like.to_user or "").strip().lower()
    game = (like.game or "battlefield").strip().lower()

    if not to_user:
        raise HTTPException(status_code=400, detail="to_user is required")

    # Lookup my username (legacy) from profiles using user_id+game
    me = (
        supabase.table("profiles")
        .select("username")
        .eq("user_id", user_id)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not me.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")

    from_user = (me.data[0].get("username") or "").strip().lower()

    if from_user == to_user:
        raise HTTPException(status_code=400, detail="You cannot like yourself")

    # Lookup target user's user_id (NEW)
    target = (
        supabase.table("profiles")
        .select("user_id")
        .eq("username", to_user)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not target.data or not target.data[0].get("user_id"):
        raise HTTPException(status_code=404, detail="Target user not found")

    to_user_id = str(target.data[0]["user_id"])

    if to_user_id in get_blocked_ids(user_id, game):
        raise HTTPException(status_code=403, detail="You can't like this player")

    payload = {
        "from_user": from_user,       # legacy
        "to_user": to_user,           # legacy
        "from_user_id": user_id,      # NEW
        "to_user_id": to_user_id,     # NEW
        "game": game
    }


    # 0) آیا طرف مقابل قبلاً منو لایک کرده؟ (برای mutual)
    reverse = (
    supabase
    .table("likes")
    .select("id")
    .eq("from_user_id", to_user_id)
    .eq("to_user_id", user_id)
    .eq("game", game)
    .limit(1)
    .execute()
    )

    reverse_exists = bool(reverse.data)

    # 1) اگر قبلاً وجود دارد، دوباره insert نکن
    exists = (
    supabase
    .table("likes")
    .select("id")
    .eq("from_user_id", user_id)
    .eq("to_user_id", to_user_id)
    .eq("game", game)
    .limit(1)
    .execute()
    )

    if exists.data:
        return {"status": "already_exists", "mutual": reverse_exists, "data": payload}

    # 2) insert
    supabase.table("likes").insert(payload).execute()

    # 3) نتیجه نهایی
    if reverse_exists:
        return {"status": "mutual", "mutual": True, "data": payload}
    return {"status": "liked", "mutual": False, "data": payload}


class LookingRequest(BaseModel):
    minutes: int = 60          # 0 = stop looking
    game: str | None = "battlefield"


@app.post(f"{API_PREFIX}/looking")
def set_looking(req: LookingRequest, user_id: str = Depends(get_current_user_id)):
    """Toggle "Looking for a squad now" for a limited time (max 3h)."""
    game = (req.game or "battlefield").strip().lower()
    minutes = max(0, min(int(req.minutes or 0), 180))
    until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat() if minutes else None

    res = (
        supabase.table("profiles")
        .update({"looking_until": until})
        .eq("user_id", user_id)
        .eq("game", game)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")
    return {"looking_now": bool(until), "looking_until": until}


class BlockRequest(BaseModel):
    to_user: str
    game: str | None = "battlefield"
    report: bool = False
    reason: str | None = None


@app.post(f"{API_PREFIX}/block")
def block_player(req: BlockRequest, user_id: str = Depends(get_current_user_id)):
    """Block (and optionally report) a player: both are hidden from each other from now on."""
    game = (req.game or "battlefield").strip().lower()
    to_user = (req.to_user or "").strip().lower()

    target = (
        supabase.table("profiles")
        .select("user_id")
        .eq("username", to_user)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not target.data or not target.data[0].get("user_id"):
        raise HTTPException(status_code=404, detail="Player not found")
    blocked_id = str(target.data[0]["user_id"])
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


BATTLEFIELD_META = {
    "game": "battlefield",
    "regions": [
        {"id": "na-west", "label": "North America West", "cities": ["Vancouver", "Seattle", "San Francisco", "Los Angeles"]},
        {"id": "na-east", "label": "North America East", "cities": ["Toronto", "New York", "Montreal"]},
        {"id": "eu-west", "label": "Europe West", "cities": ["London", "Paris", "Amsterdam"]},
        {"id": "eu-central", "label": "Europe Central", "cities": ["Frankfurt", "Berlin", "Vienna"]},
        {"id": "middle-east", "label": "Middle East", "cities": ["Istanbul", "Dubai"]},
    ],
    "languages": [
        {"code": "en", "label": "English"},
        {"code": "fa", "label": "Persian"},
        {"code": "tr", "label": "Turkish"},
        {"code": "de", "label": "German"},
        {"code": "fr", "label": "French"},
        {"code": "ar", "label": "Arabic"},
    ],
    "favorite_modes": ["Conquest", "Rush", "Breakthrough", "TDM", "Redsec"],
}


def region_label(region_id: str | None) -> str:
    for r in BATTLEFIELD_META["regions"]:
        if r["id"] == region_id:
            return r["label"]
    return region_id or ""


@app.get(f"{API_PREFIX}/meta/{{game}}")
def get_game_meta(game: str):
    if game.lower().strip() != "battlefield":
        return {"error": "Unsupported game"}
    return BATTLEFIELD_META
