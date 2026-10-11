from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from pydantic import BaseModel
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from fastapi import Header, Depends, Request, Query
from jwt import PyJWTError

import jwt
import os


# لود کردن .env از کنار همین فایل
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # از Supabase Project Settings بگیر
if not SUPABASE_JWT_SECRET:
    print("WARNING: SUPABASE_JWT_SECRET is missing. Auth endpoints will fail.")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
API_PREFIX = "/api"


# ----------------- مدل پروفایل -----------------
class GamerProfile(BaseModel):
    username: str                      # PlayMate username
    game: str | None = "battlefield"   # per-game profile
    in_game_username: str | None = None  # hidden until mutual
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

from datetime import datetime, timezone

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
def health():
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
        username = raw_username.lower()
        display_username = raw_username
        locked_username = False

    # 2) sanitize in_game_username
    in_game_username = profile.in_game_username
    if in_game_username is not None:
        in_game_username = in_game_username.strip()
        if in_game_username == "":
            in_game_username = None

    payload = {
        "user_id": user_id,
        "username": username,
        "display_username": display_username,
        "game": game,

        "in_game_username": in_game_username,
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
        .select(PUBLIC_PROFILE_FIELDS + ",in_game_username")
        .eq("user_id", user_id)
        .eq("game", game)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found for this user")
    return result.data[0]

@app.get(f"{API_PREFIX}/profiles")
def get_profiles():
    result = (
        supabase
        .table("profiles")
        .select(PUBLIC_PROFILE_FIELDS)
        .execute()
    )
    data = result.data or []
    return {"count": len(data), "data": data}

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

    for p in players:
        if (p.get("username") or "").strip().lower() == current_username:
            continue
        if str(p.get("user_id")) in liked_ids:
            continue

        score = 0
        reasons: list[str] = []

        if p.get("region") == current.region:
            score += 40
            reasons.append(f"Region match: {current.region}")

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


        matches.append({
            "username": p.get("username"),
            "match_percent": score,
            "reasons": reasons,
            "profile": safe_profile,
        })

    matches.sort(key=lambda x: x["match_percent"], reverse=True)

    return {
        "target_user": current_username,
        "game": game,
        "matches": matches[:10],
    }

from typing import Optional

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
    mates_ids = [r.get("from_user_id") for r in (in_res.data or []) if r.get("from_user_id")]

    if not mates_ids:
        return {"username": my_username, "game": game, "squadmates": []}

    prof = (
        supabase.table("profiles")
        .select(
            "username,display_username,in_game_username,profile_pic_url,wallpaper_url,"
            "region,city,languages,mic,favorite_mode,class_type,last_active"
        )
        .eq("game", game)
        .in_("user_id", mates_ids)
        .execute()
    )

    return {"username": my_username, "game": game, "squadmates": prof.data or []}


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


from typing import List, Dict
# NOTE: Query already imported at top: from fastapi import Header, Depends, Request, Query


@app.get("/api/my-squad")
def my_squad(username: str = Query(..., alias="username")):
    # GET /api/my-squad?username=Pouriya
    result = supabase.rpc(
        "find_mutual_likes",
        {"user_input": username}
    ).execute()

    rows: List[dict] = result.data or []

    return {
        "username": username,
        "squadmates": [
            {
                "me": r.get("me"),
                "squadmate": r.get("squadmate")
            }
            for r in rows
        ]
    }

@app.get("/api/my-likes")
def my_likes(username: str, game: str = "battlefield"):
    username = (username or "").strip().lower()
    game = (game or "battlefield").strip().lower()

    result = (
        supabase
        .table("likes")
        .select("to_user")
        .eq("from_user", username)
        .eq("game", game)
        .execute()
    )

    rows = result.data or []
    liked = [r.get("to_user") for r in rows if r.get("to_user")]

    return {"liked_users": liked}

@app.get(f"{API_PREFIX}/meta/{{game}}")

def get_game_meta(game: str):
    game = game.lower().strip()

    if game != "battlefield":
        return {"error": "Unsupported game"}

    return {
        "game": "battlefield",

        "regions": [
            {
                "id": "na-west",
                "label": "North America West",
                "cities": ["Vancouver", "Seattle", "San Francisco", "Los Angeles"]
            },
            {
                "id": "na-east",
                "label": "North America East",
                "cities": ["Toronto", "New York", "Montreal"]
            },
            {
                "id": "eu-west",
                "label": "Europe West",
                "cities": ["London", "Paris", "Amsterdam"]
            },
            {
                "id": "eu-central",
                "label": "Europe Central",
                "cities": ["Frankfurt", "Berlin", "Vienna"]
            },
            {
                "id": "middle-east",
                "label": "Middle East",
                "cities": ["Istanbul", "Dubai"]
            }
        ],

        "languages": [
            { "code": "en", "label": "English" },
            { "code": "fa", "label": "Persian" },
            { "code": "tr", "label": "Turkish" },
            { "code": "de", "label": "German" },
            { "code": "fr", "label": "French" },
            { "code": "ar", "label": "Arabic" }
        ],

       "favorite_modes": [
    "Conquest",
    "Rush",
    "Breakthrough",
    "TDM",
    "Redsec"
]

    }


