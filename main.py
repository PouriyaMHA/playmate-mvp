from fastapi.responses import HTMLResponse
from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
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
@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    # همین ui.html که فرستادی باید کنار main.py باشه
    html_path = Path(__file__).parent / "ui.html"
    return html_path.read_text(encoding="utf-8")

@app.get("/profile-full")
def profile_full(username: str):
    result = supabase.table("profiles").select("*").eq("username", username).execute()
    if not result.data:
        return {"error": "user not found"}
    return result.data[0]


@app.get("/", response_class=HTMLResponse)
def landing():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>PlayMate BF – Find your Battlefield squad</title>
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      padding: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top, #111827 0, #020617 40%, #000 100%);
      color: #e5e7eb;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .shell {
      max-width: 900px;
      width: 100%;
      padding: 24px;
    }
    .card-landing {
      background: rgba(15, 23, 42, 0.98);
      border-radius: 20px;
      border: 1px solid #1f2933;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
      padding: 28px 28px 22px;
      display: grid;
      grid-template-columns: minmax(0, 3fr) minmax(0, 2.2fr);
      gap: 24px;
    }
    .logo-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 4px 10px;
      border-radius: 999px;
      background: #020617;
      border: 1px solid #1f2937;
      font-size: 11px;
      color: #9ca3af;
      margin-bottom: 10px;
    }
    .logo-circle {
      width: 22px;
      height: 22px;
      border-radius: 999px;
      background: linear-gradient(135deg, #22c55e, #4ade80);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #020617;
      font-weight: 800;
      font-size: 11px;
    }
    h1 {
      font-size: 30px;
      margin: 0 0 6px;
    }
    .headline-highlight {
      color: #4ade80;
    }
    .sub {
      font-size: 13px;
      color: #9ca3af;
      margin-bottom: 18px;
      max-width: 480px;
    }
    .points {
      font-size: 12px;
      color: #9ca3af;
      display: grid;
      gap: 6px;
      margin-bottom: 20px;
    }
    .point-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .point-dot {
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: #4ade80;
    }
    .cta-row {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .btn-main {
      background: #22c55e;
      color: #020617;
      border-radius: 999px;
      padding: 10px 24px;
      font-weight: 700;
      font-size: 14px;
      border: none;
      cursor: pointer;
      box-shadow: 0 20px 45px rgba(22, 163, 74, 0.6);
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .btn-main:hover {
      background: #16a34a;
      transform: translateY(-1px);
      box-shadow: 0 24px 55px rgba(22, 163, 74, 0.7);
    }
    .btn-main:active {
      transform: translateY(0);
      box-shadow: 0 16px 35px rgba(22, 163, 74, 0.5);
    }
    .btn-arrow {
      font-size: 14px;
    }
    .cta-caption {
      font-size: 11px;
      color: #9ca3af;
    }
    .right-col {
      border-radius: 16px;
      background: radial-gradient(circle at top, rgba(34, 197, 94, 0.16), transparent 55%),
                  linear-gradient(145deg, #020617, #020617);
      border: 1px solid #1f2933;
      padding: 14px 14px 10px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      font-size: 11px;
    }
    .right-title {
      font-size: 12px;
      font-weight: 600;
      color: #e5e7eb;
    }
    .right-pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .right-pill {
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid #1f2937;
      background: #020617;
      color: #9ca3af;
      font-size: 11px;
    }
    .right-meta {
      margin-top: 6px;
      display: grid;
      gap: 3px;
    }
    .meta-line {
      color: #6b7280;
    }
    .meta-strong {
      color: #e5e7eb;
      font-weight: 500;
    }
    @media (max-width: 780px) {
      .card-landing {
        grid-template-columns: minmax(0, 1fr);
      }
      .shell {
        padding: 16px;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="card-landing">
      <div>
        <div class="logo-pill">
          <div class="logo-circle">PM</div>
          <span>PlayMate BF · MVP</span>
        </div>
        <h1>
          Find your <span class="headline-highlight">Battlefield squad</span><br />
          in under 30 seconds.
        </h1>
        <p class="sub">
          PlayMate BF matches Battlefield players by region, favorite mode, class, language and mic – 
          so you can skip random lobbies and build a real squad.
        </p>
        <div class="points">
          <div class="point-row">
            <div class="point-dot"></div>
            <div>Smart matching based on region, mode, class, mic and languages.</div>
          </div>
          <div class="point-row">
            <div class="point-dot"></div>
            <div>Swipe through your best matches, then add them to your squad.</div>
          </div>
          <div class="point-row">
            <div class="point-dot"></div>
            <div>See mutual likes in <b>My Squad</b> when both of you add each other.</div>
          </div>
        </div>
        <div class="cta-row">
          <button class="btn-main" onclick="window.location.href='/ui'">
            Start matchmaking
            <span class="btn-arrow">→</span>
          </button>
          <div class="cta-caption">
            No login yet. Just set your Battlefield profile and start matching.
          </div>
        </div>
      </div>
      <div class="right-col">
        <div class="right-title">What you’ll see inside</div>
        <div class="right-pill-row">
          <div class="right-pill">Battlefield profile form</div>
          <div class="right-pill">Match list (0–100%)</div>
          <div class="right-pill">Swipe mode (beta)</div>
          <div class="right-pill">My Squad · mutual likes</div>
        </div>
        <div class="right-meta">
          <div class="meta-line">
            <span class="meta-strong">Match inputs:</span> region, platform, favorite mode, class, mic, languages.
          </div>
          <div class="meta-line">
            <span class="meta-strong">Perfect for:</span> players tired of random teammates & solo queue.
          </div>
          <div class="meta-line">
            <span class="meta-strong">Current scope:</span> Battlefield only. Designed to extend to more games later.
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
    """


@app.post("/profile")
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


@app.get("/profiles")
def list_profiles():
    result = supabase.table("profiles").select("*").execute()
    return {"count": len(result.data), "data": result.data}


@app.post("/match")
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


@app.post("/like")
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

from typing import List

@app.get("/my-squad")
def my_squad(username: str):
    # مثال: GET /my-squad?username=Pouriya
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


