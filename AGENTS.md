# Agent instructions

- Project context and review brief: read `docs/CODEX_REVIEW_BRIEF.md` first, then `CLAUDE.md` (code rules) and
  `docs/PROJECT_HISTORY.md`.
- This repo deploys to production on every push to `main`, and the local `.env` points to the production database:
  **don't push, don't write to the database, don't create accounts, never print secrets.** Report findings in a
  Markdown file instead (for example `docs/CODEX_REVIEW.md`).
