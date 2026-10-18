# PlayMate

Gaming teammate matchmaking (12 games, Battlefield 6 first). FastAPI + Supabase (DB + Auth) + plain HTML/CSS/JS, deployed on Render from GitHub `PouriyaMHA/playmate-mvp` (`main`, auto-deploy).
Full background, decisions and open issues: `docs/PROJECT_HISTORY.md`. Raw ChatGPT history (local only): `docs/chatgpt-history/`.

## Layout
- `main.py` — all routes. Pages: `/` landing.html, `/app` (and old `/bf`) ui.html, `/u/<username>` (and `/profile?username=`) profile.html, `/terms` `/privacy` legal.html. APIs under `/api`; protected ones use `Depends(get_current_user_id)` (Supabase JWT, HS256).
- `games.py` — supported games: platforms, in-game-name label and per-game field templates. Adding a game = add an entry + art in `static/img/games/<id>.svg` and `<id>-icon.svg`; optional official cover `static/img/games/photos/<id>.jpg` (960×540, used when present, SVG is the fallback — bump `COVER_VERSION` when one changes).
- `static/css` `static/js` — one CSS/JS pair per page (`ui.*`, `profile.*`, `landing.*`; `ui.css` holds the shared tokens). Bump `?v=` in the HTML when you change them.
- `static/img` — original SVG art (games, banners, avatars, badges, logo); `tools/gen_art.py` regenerates it.
- Data: `profiles` (one row per user + game; game-specific values in `game_meta.fields`), `likes`, `blocks` (RLS on, server uses the secret key). Account data (bio, banner, avatar, links, referral) lives in the auth user's `app_metadata.playmate` (only the server can write it).
- Run locally: `uvicorn main:app --reload` (needs `.env` with SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET).

## Rules
- Identity comes from the JWT `user_id`, never from request bodies or query params.
- Never expose `in_game_username` / `discord_username` outside the owner (`/api/my-profile`) and mutual squadmates (`/api/my-squad-details`).
- Escape every user-provided value rendered with innerHTML (`esc()`).
- Browser code may only use the Supabase anon/publishable key.
- User-facing UI text in English.
- Destructive SQL: preview with SELECT first and scope tightly. Supabase `app_metadata` updates MERGE keys — remove a key by setting it to `None`.

## Working with the user
- Replies in Persian; code and identifiers in English.
- Base every change on the actual current files — never assume code exists.
- When explaining a change the user will make by hand, show exact Before/After and where it goes.
