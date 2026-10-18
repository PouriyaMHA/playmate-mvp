# Agent instructions (Codex)

- Project context: read `docs/CODEX_REVIEW_BRIEF.md` first, then `CLAUDE.md` (code rules) and `docs/PROJECT_HISTORY.md`.

## How Claude and Codex work together
- **Claude Code builds; Codex reviews and tests.** Claude calls you with `codex exec` / `codex review` and acts on
  your report. The owner wants you to **challenge each other**: say clearly when you think Claude's approach or
  decision is wrong and what would be better, with evidence (file:line, a failing scenario, an official source).
  Claude will either fix it or answer with its reasons in the next round. The better, correct solution wins; when
  you two still disagree, both opinions go to the owner.
- Write your results only to the file you are asked to (normally `docs/reviews/<date>-<topic>.md`).
  **Don't edit any other file.** Claude makes the code changes.

## Ground rules (production)
- Every push to `main` deploys to the live site: **never commit or push.**
- The local `.env` points to the production database: **don't read or print `.env`, don't use the service key, don't
  run SQL or write to the database directly.**
- **Live testing as a user is allowed and wanted** (owner, 2026-10-18 — there are no real users yet):
  - You may sign up throwaway test accounts on https://playmate-api-aamc.onrender.com (use `@example.com` emails and
    names starting with `qa`), create profiles, like, match, block, report and unblock **between your own test
    accounts**.
  - **Don't like, block or report the existing real profiles** (pouriya, akbari, behrooz, ppppp).
  - **Delete every test account you created at the end** (Settings → Delete account, or `DELETE /api/account` with
    that account's own token), and say in your report that they are gone.
