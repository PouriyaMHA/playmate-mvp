# PlayMate — Project History (from ChatGPT project "PlayMate (Main)")

Consolidated from the 9 ChatGPT chats (Dec 2025 → Apr 2026). Raw transcripts are in `docs/chatgpt-history/` (secrets redacted, some long code blocks trimmed).

## What PlayMate is
A gaming teammate-matchmaking + social platform. First game: **Battlefield** ("PlayMate BF"). Players build a per-game profile and get scored matches; mutual likes become a **Squad**. Long-term vision: account layer (login, subscriptions, referrals, store, wallet) → per-game profiles → discovery (swipe, scoring, block/skip) → presentation (landing, game selector, profile pages, store).

## Stack & deploy
- Backend: FastAPI `main.py` (serves HTML too). Frontend: plain HTML/CSS/JS — `landing.html` (`/`), `ui.html` (`/bf`), `profile.html` (`/profile?username=`).
- Supabase: Postgres + Auth (JWT HS256 verified with the **Legacy JWT Secret**, env `SUPABASE_JWT_SECRET`). Env: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`.
- GitHub `PouriyaMHA/playmate-mvp` (branch `main`) → Render auto-deploy: `https://playmate-api-aamc.onrender.com`. Build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Browser must only use the Supabase **publishable/anon** key (a secret key in the browser was a past mistake; rotating exposed keys was advised).

## Timeline
1. **Phase 1 – baseline & deploy (chat 01).** `profiles` table, scoring (region +40, mode +25, class +15, shared language +10, both voice +10, cap 100, top 10 with reasons). `likes` table, RPC `find_mutual_likes`, My Squad, `/my-likes`, swipe mode (≥50%, not already liked), localStorage profile, Top picks, landing page. Git/GitHub/Render setup. Routing: `/` landing, `/bf` UI, `/ui`→`/bf`, APIs under `/api`.
2. **Phase 2 (chat 02).** Front-end fail-safe (`fetchJson` with timeouts, error classification), submit lock. Profile upsert + unique indexes (an over-broad DELETE wiped test profiles — be careful with destructive SQL). Likes select-then-insert. Per-game columns: `game, city, in_game_username, profile_pic_url, wallpaper_url, game_meta, last_active`. `GET /api/meta/{game}` (regions+cities, languages, modes incl. "Redsec"), region→city cascade, languages multi-select (CSV codes).
3. **Step 6 (chat 03).** Usernames lowercased + `display_username`; unique (lower(username), game); IGN unique per game (partial index `profiles_game_ign_unique`) → backend 409 + toast. IGN hidden everywhere except mutual squad (field whitelists). Step 7 profile page + "View profile" link. Step 8 mutual logic in `/api/like` (`liked`/`mutual`/`already_exists`). Step 9 online status = PlayMate activity (`last_active`, `/api/ping`).
4. **UI redesign (chats 04, 05).** Neon/glassmorphism 3-column `/bf` (profile | swipe card | squad), "IT'S A MATCH!" modal with electric-link SVG + fireworks, meta-driven form, realtime ping + squad refresh, humanized last seen, Step 9D public profile page, logo/icon prompts (PM Interlock monogram).
5. **Step 9E (chat 07).** Single realtime interval, `inFlight` guards, net banner, empty states. Then **Step 10A auth**: `profiles.user_id`, `likes.from_user_id/to_user_id`, JWT dependency `get_current_user_id`, upsert on `(user_id, game)`, Supabase Auth on landing.
6. **Anti-spoof + auth stabilization (chats 06, 08).** Identity always from JWT (never request body); `authFetch` (Bearer, 401 → logout); username chosen at signup (`user_metadata.pm_username`) and locked; "LIKE SENT" vs "IT'S A MATCH!" modal; logout; login/signup mode toggle; `/profile-squad` public mutual list.
7. **Chat 09 (Apr 28 2026).** Project summary; next goals listed below.

## Status when work moved to Claude Code (Oct 2026)
Working tree (`E:\MVP PlayMate\playmate-mvp`, copied here) has **large uncommitted changes** vs last commit `a054ce7 Step 9E`. Verified against the actual files:
- ✅ `main.py`: JWT auth, user_id-based like/squad, `/profile-squad` via user_id, no dead code in `my_squad_details`.
- ✅ `profile.html` uses `/profile-squad`. ✅ Logout button exists and is wired. ✅ Landing has mode-based `handleAuth`.
- ❌ `requirements.txt` lacks **PyJWT** → `import jwt` will crash on Render.
- ❌ `landing.html` auth card is duplicated/nested (two headers, two mode toggles with duplicate IDs, a `<form id="authForm">` inside another).
- ❌ `/api/match` doesn't exclude already-liked players (re-show / re-like).
- ❌ `favorite_mode` not `required`; `saveProfile` doesn't validate region/favorite_mode; backend doesn't reject empty values.
- ❌ 404 (no profile yet) from ping/squad is shown as "Connection issue".
- ❌ `handleLike`: a non-OK response returns before releasing `inFlight.like` → like/skip stuck after one failure.
- ❌ Mutual modal shows IGN "—" (match payload hides IGN; should read from refreshed squad).
- Leftovers: legacy `/api/my-squad` (RPC) and `/api/my-likes` (username-based, unauthenticated); `ALLOWED_PUBLIC_FIELDS` defined inside the loop; `test_env.py` prints the key.

**2026-10-11:** the uncommitted ChatGPT-era work was committed as `Step 10A auth work…`, then all 7 ❌ items above were fixed in the next commit (not yet pushed/deployed; Supabase project appeared paused — host did not resolve).

## Roadmap
1. ~~Fix the ❌ items above~~, restore Supabase project, push/deploy, two-account E2E test.
2. **Pending Likes** section under My Squad (incoming vs outgoing — undecided).
3. Step 10A finish (user_id everywhere, drop legacy endpoints) → 10B multi-game → 10C smarter scoring + analytics.
4. Later: UI/UX polish, account/settings pages (`/account`, `/settings`), squad chat, notifications, customization (wallpapers/themes store), referrals, mobile, i18n at the end (UI text English only for now).

## Decisions to respect
- Platform optional/display-only (cross-play). Playstyle & available-time dropped.
- IGN revealed only to mutual squadmates. "Match" means mutual.
- Username lowercase canonical + `display_username`; locked after signup.
- UI has no scoring/privacy logic; backend decides.
- City optional/informational; region drives scoring.
