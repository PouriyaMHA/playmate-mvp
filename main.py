from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import os


# لود کردن .env از کنار همین فایل
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_KEY is None? ", SUPABASE_KEY is None)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
API_PREFIX = "/api"


# ----------------- مدل پروفایل -----------------
class GamerProfile(BaseModel):
    username: str
    platform: str | None = None   # اختیاری، فقط برای نمایش
    region: str                   # Turkey / EU West / NA West ...
    favorite_mode: str            # Conquest / Rush / Breakthrough ...
    class_type: str               # assault / engineer / support / recon
    mic: str                      # voice / text / both / none
    languages: str                # مثل: "en,fa" یا "en" یا "fa,tr"


# ----------------- توابع کمکی -----------------
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


@app.get("/profile-full")
def profile_full(username: str):
    result = supabase.table("profiles").select("*").eq("username", username).execute()
    if not result.data:
        return {"error": "user not found"}
    return result.data[0]

@app.get("/health")
def health():
    return {"status": "ok"}



@app.post("/api/profile")
def create_profile(profile: GamerProfile):

    result = supabase.table("profiles").insert({
        "username": profile.username,
        "platform": profile.platform,
        "region": profile.region,
        "favorite_mode": profile.favorite_mode,
        "class_type": profile.class_type,
        "mic": profile.mic,
        "languages": profile.languages,
    }).execute()

    return {"status": "saved", "data": result.data}


@app.get(f"{API_PREFIX}/profiles")
def list_profiles():
    result = supabase.table("profiles").select("*").execute()
    return {"count": len(result.data), "data": result.data}


@app.post("/api/match")
def match_players(current: GamerProfile):

    # گرفتن همه‌ی پروفایل‌ها از دیتابیس
    result = supabase.table("profiles").select("*").execute()
    players = result.data or []

    current_langs = parse_languages(current.languages)
    voice_set = {"voice", "both"}

    matches = []

    for p in players:
        # خودش رو از لیست حذف کن
        if p.get("username") == current.username:
            continue

        score = 0
        reasons: list[str] = []

        # 1) Region
        if p.get("region") == current.region:
            score += 40
            reasons.append(f"Region match: {current.region}")

        # 2) favorite_mode
        if p.get("favorite_mode") == current.favorite_mode:
            score += 25
            reasons.append(f"Same favorite mode: {current.favorite_mode}")

        # 3) class_type
        if p.get("class_type") == current.class_type:
            score += 15
            reasons.append(f"Same class: {current.class_type}")

        # 4) languages
        other_langs = parse_languages(p.get("languages", ""))
        common_langs = sorted(set(current_langs) & set(other_langs))
        if common_langs:
            score += 10
            reasons.append("Common languages: " + ", ".join(common_langs))

        # 5) mic
        mic_current = (current.mic or "").lower()
        mic_other = (p.get("mic") or "").lower()

        if mic_current in voice_set and mic_other in voice_set:
            score += 10
            reasons.append("Both can use voice chat")

        # مطمئن شو از 0 تا 100 بیرون نره (برای احتیاط)
        if score > 100:
            score = 100

        matches.append({
            "username": p.get("username"),
            "match_percent": score,
            "reasons": reasons,
            "profile": p,   # کل پروفایل طرف مقابل
        })

    # مرتب‌سازی بر اساس درصد مچ
    matches.sort(key=lambda x: x["match_percent"], reverse=True)

    return {
        "target_user": current.username,
        "matches": matches[:10]  # حداکثر ۱۰ تا
    }


# ----------------- مدل لایک / افزودن اسکادمیت -----------------
class LikeRequest(BaseModel):
    from_user: str      # پلی‌میت یوزرنیم خودت
    to_user: str        # کسی که می‌خوای add کنی
    game: str | None = "battlefield"


@app.post("/api/like")
def add_like(like: LikeRequest):

    payload = {
        "from_user": like.from_user,
        "to_user": like.to_user,
        "game": like.game or "battlefield",
    }

    try:
        result = supabase.table("likes").insert(payload).execute()
        return {"status": "inserted", "data": result.data}
    except Exception as e:
        # اگر بخاطر unique constraint خطا داد، یعنی قبلاً وجود داشته
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg:
            return {"status": "already_exists", "data": payload}
        # هر خطای دیگه رو هم برگردونیم برای دیباگ
        return {"status": "error", "error": str(e)}

from typing import List, Dict
from fastapi import Query

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

@app.get("/my-likes")
def my_likes(username: str, game: str = "battlefield"):
    result = (
        supabase
        .table("likes")
        .select("to_user")
        .eq("from_user", username)
        .eq("game", game)
        .execute()
    )
    rows = result.data or []
    return {
        "username": username,
        "liked_users": [r["to_user"] for r in rows]
    }


