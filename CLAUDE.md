# PlayMate

Gaming teammate matchmaking (Battlefield first). FastAPI + Supabase (DB + Auth) + plain HTML/JS, deployed on Render from GitHub `PouriyaMHA/playmate-mvp` (`main`).
Full background, decisions and open issues: `docs/PROJECT_HISTORY.md`. Raw ChatGPT history: `docs/chatgpt-history/`.

## Layout
- `main.py` — all routes. Pages: `/` landing.html, `/bf` ui.html, `/profile` profile.html. APIs under `/api`; protected ones use `Depends(get_current_user_id)` (Supabase JWT, HS256).
- Run locally: `uvicorn main:app --reload` (needs `.env` with SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET).

## Rules
- Identity comes from the JWT `user_id`, never from request bodies or query params.
- Never expose `in_game_username` outside mutual-squad responses; select whitelisted fields.
- Browser code may only use the Supabase anon/publishable key.
- User-facing UI text in English.
- Destructive SQL: preview with SELECT first and scope tightly.

## Working with the user
- Replies in Persian; code and identifiers in English.
- Base every change on the actual current files — never assume code exists.
- When explaining a change the user will make by hand, show exact Before/After and where it goes.
