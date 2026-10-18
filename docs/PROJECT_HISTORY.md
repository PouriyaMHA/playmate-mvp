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

Same day, deployed to Render (`SUPABASE_JWT_SECRET` added there): `/api/my-profile` (profile loads from server), Pending Likes (`/api/pending-likes`), IGN removed from public `/profile-squad`, session refresh past the 1-hour token expiry, My Squad no longer empty after reload, cached profile cleared on logout. Live E2E run with two accounts (pouriya + test user) passed; signup/login screens themselves still need a manual check.

Later same day: RLS enabled on `likes` (was fully open to the public anon key); legacy unauthenticated endpoints removed; new `Looking now` status (`profiles.looking_until`, `/api/looking`), optional Discord (`profiles.discord_username`, mutual-only) with copy buttons, Block/Report (`blocks` table, `/api/block`); XSS fixes in ui.html/profile.html; stale HTTP/2 Supabase connection (random 500s) fixed; GitHub Actions keep-alive every 10 min. Confirm email intentionally still OFF until public launch. Next: full UI/UX redesign (target 10/10, mobile, onboarding, split ui.html).

2026-10-12/13: Find Matches page redesigned (neon glass, per the user's mockup), match modal with energy beam + original fireworks, compact layout for short laptop screens; live E2E passed.

2026-10-14/15 (6-hour build session, based on the planning summary `PlayMate-Summary.pdf`):
- **Multi-game:** 12 games in `games.py` (Battlefield 6, CS2, Fortnite, Apex, PUBG Mobile, CODM, Minecraft, LoL, Helldivers 2, EA SPORTS FC 27 (the `fc` slot always holds the newest FC), GTA Online, Rocket League — last three added 2026-10-18), each with its own platforms, in-game-name label and field template (mode/rank/server…). Locations (2026-10-18): Region → Country (required) → City (optional) from `locations.py`, 9 regions incl. Africa, ~80 countries, big Iran city list; same country = +5 in matching. Role fields were removed 2026-10-18 except LoL role, FC position and BF class (optional); those use `match="diff"` = points for DIFFERENT roles, stored in `profiles.game_meta.fields`. Username shared across games. Game picker with cover art; prefill shared fields from another game.
- **Matching:** uses my saved profile; region 35, city +5, languages 15–20, voice 10, platform 5, game fields (weights per game). Filters: same language only, looking-now only. No minimum score (small user base) — instead a smart empty state (Looking now / invite / add game) and live stats.
- **Profiles:** `/u/<name>` with banner, avatar (12 SVG presets + 13 illustrated WebP avatars added 2026-10-18, shown on match cards/squad/modal too; photo upload = placeholder), bio, links (Twitch/YouTube/Instagram), badges (Early Member, First Match, Squad Leader; Verified/Legendary = placeholders), per-game cards, Highlights tab (placeholder), Squad tab. Owner edit drawer. Account data in auth `app_metadata.playmate`.
- **Invites:** `/?ref=<username>` captured on landing, saved after first profile save; invite card with referral count.
- **Landing** rebuilt (games showcase, how it works, safety), inline auth errors, password reset, removed public "Quick Dev Account". Draft `/terms` `/privacy`.
- **Mobile:** bottom tabs (Profile / Match / Squad), sticky Skip/Like.
- **Background alerts:** 60s polling in hidden tabs, tab-title flag + optional system notification.
- Original SVG art in `static/img` (`tools/gen_art.py`).

Decision log from the planning summary: mobile app postponed (responsive web first); per-game cards inside one profile (no page per game); in-person meetups NOT pursued for now (minors/safety) — city is only for ping/region; add games gradually but all 9 are listed.

2026-10-18 — external review by Codex (`docs/CODEX_REVIEW.md`, 6.5/10, no Critical). Phase 1 fixed the same day:
H01 logout now wipes every account cache + revokes the session, and a different account on the same device never sees
the previous one's cached Discord/location (`pm_uid` owner check); H02 stale responses after a game switch are dropped;
M03 double Skip; M04 Find Matches locked while saving; M01 platform required server-side + GTA PC split into
Enhanced/Legacy; M07 JWT must have aud=authenticated, exp, UUID sub; M09 Auth outages return 503 instead of "not found"
(avatar no longer wiped); M11 a later plain block keeps an earlier report; M12 password recovery can't be hijacked by the
Sign up tab; M15 CSP/nosniff/frame/HSTS headers, API `no-store`, SRI on supabase-js; L06 test_env.py no longer prints
keys; L07 avatar in LIKE SENT modal. Phase 2 (same day): "Liked you" list with Like back / Pass (`/api/incoming-likes`),
people who already like you are flagged and sorted first in the deck; skipped players are remembered per tab and
"Show more" pages past them (`exclude`, `has_more`); Unmatch (`DELETE /api/like`, removes both likes); standalone
`/settings` (account, log out, what's public, blocked players + Unblock via `GET /api/blocks` / `DELETE /api/block` —
reported players stay blocked, delete account); a logged-in blocked viewer gets 404 on the other's public profile;
honest Block copy; "Like" instead of "Add to squad"; Report is an in-app form with reasons; squad shows "No contact
added yet" and saving without IGN/Discord nudges; likes are idempotent and "mutual" is decided after the insert; fixed
the squad list not redrawing after the last squadmate was removed (empty-signature bug). Phase 3 (same day):
`db/migrations/001_accounts_and_constraints.sql` (accounts table = reserved username that survives removing every game,
unique likes, indexes) — the code detects the table and falls back until the owner runs it; pinned requirements;
pytest suite on an in-memory fake Supabase (tests/, 46 tests) + GitHub Actions; `/api/poll` replaces 4 requests per
15-second tick (~18 → ~6 DB queries) and the public counters are cached; accessibility (focus moves into dialogs and
back, aria-pressed/selected, live region for toasts, --faint contrast ≥ 4.5:1, password toggle label); Highlights
placeholder and the disabled photo-upload button removed; profile pages get the player's name in <title>/OG tags and a
real 404; the chosen game survives sign-up. Earlier phase-3 plan: accounts table for usernames (H03), pinned deps + automated
tests + schema in repo (M14), fewer Supabase round trips (M08), accessibility (M13).

2026-10-18 (later) — Claude ↔ Codex review loop (`docs/reviews/`, rounds 2–5; Codex tests the live site with throwaway
`qa…@example.com` accounts and deletes them). Round 3/4 fixes: `social_snapshot` SQL function (migration 002) = likes +
blocks + profiles in ONE statement (contact info can't be pieced together from different moments; no 1000-row cap);
authenticated pages pin their account (`pageUid`) so nothing is ever sent with another account's token (incl. 401
refresh retries, other tabs); game-switch generations cover errors/timers/A→B→A; Skip/Like timers check card identity;
public squads respect the viewer's blocks; `state.gameReady`. Testing: real-Chromium browser tests (Playwright) and an
`integration` CI job on a real Postgres + PostgREST (`tests/integration/schema.sql` copied from the production catalog +
all migrations). Rate limits on every write route (per account) and public reads (per IP). Account deletion in one
transaction (`delete_account_data`, migration 003). Migrations 001–003 have all been run on production.

## Roadmap
1. Before public launch: turn on Supabase **Confirm email**; ~~reliable keep-alive~~ done 2026-10-17 (cron-job.org, every 10 min, `/health?deep=1`); finalise Terms/Privacy; manual check of Sign up / Log in / password reset.
2. Grow: invite rewards (badges for referrals), share cards, Persian community marketing.
3. Profile photo upload (Supabase Storage + report/moderation), highlights upload.
4. Squad chat / notifications by email, rank verification ("Verified" badge). (Self-service account deletion: done 2026-10-18.)
6. Open from the reviews: append-only reports/moderation queue + a support contact; Render "deploy only after CI passes"
   (Render dashboard setting — owner); own domain.
5. Later: i18n (UI English only for now), mobile app.

## Decisions to respect
- Platform is scored lightly; hard crossplay filters only where a game has no crossplay (GTA Online; FC Switch) plus must-match fields (Minecraft edition, LoL server) — added 2026-10-18. Playstyle & available-time dropped (user declined a "when do you play" field again on 2026-10-18).
- IGN revealed only to mutual squadmates. "Match" means mutual.
- Username lowercase canonical + `display_username`; locked after signup.
- UI has no scoring/privacy logic; backend decides.
- City optional/informational; region drives scoring.
