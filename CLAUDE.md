# PlayMate

Gaming teammate matchmaking (12 games, Battlefield 6 first). FastAPI + Supabase (DB + Auth) + plain HTML/CSS/JS, deployed on Render from GitHub `PouriyaMHA/playmate-mvp` (`main`, auto-deploy).
Full background, decisions and open issues: `docs/PROJECT_HISTORY.md`. Raw ChatGPT history (local only): `docs/chatgpt-history/`.

## Layout
- `main.py` — all routes. Pages: `/` landing.html, `/app` (and old `/bf`) ui.html, `/u/<username>` (and `/profile?username=`) profile.html, `/settings` settings.html, `/terms` `/privacy` legal.html. APIs under `/api`; protected ones use `Depends(get_current_user_id)` (Supabase JWT, HS256).
- `locations.py` — Region → Country → City lists (country is stored in `profiles.game_meta.country`; older rows derive it from their city).
- `games.py` — supported games: platforms, in-game-name label and per-game field templates. Adding a game = add an entry + art in `static/img/games/<id>.svg` and `<id>-icon.svg`; optional official cover `static/img/games/photos/<id>.jpg` (960×540, used when present, SVG is the fallback — bump `COVER_VERSION` when one changes).
- `static/css` `static/js` — one CSS/JS pair per page (`ui.*`, `profile.*`, `landing.*`; `ui.css` holds the shared tokens). Bump `?v=` in the HTML when you change them.
- `static/img` — original SVG art (games, banners, avatars, badges, logo); `tools/gen_art.py` regenerates it.
- Data: `accounts` (one row per user: the reserved username — after migration 001), `profiles` (one row per user + game; game-specific values in `game_meta.fields`), `likes`, `blocks` (RLS on, server uses the secret key). The app refreshes squad/pending/"liked you" with one `GET /api/poll` every 15 s; the server reads likes + blocks + profiles for it through ONE SQL function, `social_snapshot` (migration 002, service role only) — never piece contact info together from separate reads. Account data (bio, banner, avatar, links, referral) lives in the auth user's `app_metadata.playmate` (only the server can write it).
- Run locally: `uvicorn main:app --reload` (needs `.env` with SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET).
- Tests: `python -m pytest` (installs from `requirements-dev.txt`). They run against an in-memory fake DB (`tests/fakedb.py`) —
  never the real Supabase — and run in GitHub Actions on every push (`.github/workflows/tests.yml`). Add a test with every change.
  Frontend behavior is tested in real headless Chromium (`tests/test_browser.py`, helpers in `tests/browser_support.py`:
  fake supabase-js `window.__auth`, `__hold(pattern)`/`__release` to hold a fetch). Locally once: `python -m playwright install chromium`.
- Database changes: SQL files in `db/migrations/` (numbered), run in Supabase → SQL Editor. Ship code that needs a new
  table only after the migration ran (001 and 002 ran 2026-10-18; `accounts` and `social_snapshot` are required — no silent fallbacks).
  The fake DB mirrors the unique constraints and PostgREST's 1000-row cap.
- Security headers: CSP has no `'unsafe-inline'` for scripts — never add inline `<script>` or `on*=` handlers;
  use listeners (image fallbacks: `data-fallback` attribute).
- Authenticated pages (`ui.js`, `profile.js`, `settings.js`) pin the page's account (`pageUid`): never send a request,
  including a 401-refresh retry, with a token of another account — reload instead.
- `requirements.txt` pins exact versions; upgrade on purpose and run the tests.
- Rate limits (`main.check_rate`, in memory — one Render process): every write route has `dependencies=[limit(...)]`
  (per account) and public reads `limit_ip(...)`. Give every new route one; 429 + Retry-After when exceeded.
- CI has two jobs: `test` (fake DB + real Chromium) and `integration` (real Postgres + PostgREST from
  `tests/integration/schema.sql` + all migrations; `tests/test_integration_pg.py`). A new migration must keep both green.

## Rules
- Identity comes from the JWT `user_id`, never from request bodies or query params.
- Never expose `in_game_username` / `discord_username` outside the owner (`/api/my-profile`) and mutual squadmates (`/api/my-squad-details`).
- Escape every user-provided value rendered with innerHTML (`esc()`).
- Browser code may only use the Supabase anon/publishable key.
- User-facing UI text in English.
- Destructive SQL: preview with SELECT first and scope tightly. Supabase `app_metadata` updates MERGE keys — remove a key by setting it to `None`.

## Working with Codex
- Codex (OpenAI) is the reviewer/tester; Claude builds. Call it with
  `& "$env:LOCALAPPDATA\OpenAI\Codex\bin\<hash>\codex.exe" exec -C <repo> -s workspace-write -o <file> "<prompt>"`
  (or `codex review --base main` / `--commit <sha>`). Its rules are in `AGENTS.md`; reviews go to `docs/reviews/`.
- Ask Codex to review important changes (security, data, matching, payments) before or right after pushing.
- Challenge each other: verify every Codex finding against the code before acting; fix what's right, push back with
  evidence on what isn't, and write the answer under `## Claude's response` in the review file. Disagreements → owner.

## Working with the user
- Replies in Persian; code and identifiers in English.
- Base every change on the actual current files — never assume code exists.
- When explaining a change the user will make by hand, show exact Before/After and where it goes.
