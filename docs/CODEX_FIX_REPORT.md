# PlayMate — fixes after the Codex review (for re-verification)

Your report: `docs/CODEX_REVIEW.md` (reviewed commit `f76de29`). The fixes are in three commits on `main`, all deployed:

| Commit | What |
|---|---|
| `26d3d1b` | Phase 1 — security and correctness |
| `3f46e38` | Phase 2 — the match loop (incoming likes, unmatch, settings, report form) |
| `8279841` | Phase 3 — accounts table, tests + CI, fewer DB calls, accessibility |

**Database migration** `db/migrations/001_accounts_and_constraints.sql` was run on production on 2026-10-18. Result:
4 players = 4 account rows; duplicate likes are now rejected by a unique index.

**Please re-check everything below.** Tell us what is really fixed and what is fixed badly or only partly. Also look
for anything the changes broke, or new problems in the new code (section C). Same ground rules as `AGENTS.md`:
- Don't push.
- Don't write to the database unless the owner allows it.
- If you create test accounts with permission, delete them afterwards via **Settings → Delete account**.

Status legend: ✅ fixed · 🟡 partly fixed (the open part is listed) · ⏸ not fixed on purpose / deferred (reason given).

---

## A. Your findings

### High
| ID | Status | What changed | Where |
|---|---|---|---|
| **H01** cached data leaks to the next account | ✅ | **Logout:** calls `supabase.auth.signOut()` (revokes the refresh token, 1.5 s timeout), then wipes every `pm_*`, `playmate_*` and `sb-*` key and `sessionStorage`. **Account switch on the same device without logging out** (e.g. an expired session) is also handled: `pm_uid` stores the last account's id. On app load (`ensureCacheOwner`) and on login (`storeSession`), a different id wipes the old caches. **Prefill cache:** `playmate_shared` carries a `uid` and is only used when it matches the current token's `sub`. | `static/js/ui.js` (`clearAccountCache`, `tokenUserId`, `ensureCacheOwner`, `clearAuthAndRedirect`, `loadProfileForGame`), `static/js/landing.js` (`storeSession`), `static/js/settings.js` (`forgetDevice`) |
| **H02** stale responses after a game switch | ✅ | **Game metadata, profile load, like, Looking-now:** each one captures `game` at the start and drops its result if `state.game` changed after an `await`. **Like:** the delayed swipe step also checks the card index. **Matches:** a match request that finishes for the previous game is discarded and re-run for the current one. **Not used:** AbortController — we discard stale results instead of cancelling the request. | `ui.js` (`selectGame`, `loadProfileForGame`, `handleLike`, `toggleLooking`, `findMatches`) |
| **H03** username not reserved / not atomic | ✅ | **New `accounts` table** (`user_id` PK → `auth.users` with `on delete cascade`, `username` unique, lowercase check). **Claiming the name:** `claim_username()` inserts the row right before the profile upsert, after all validation passed; a unique violation returns 409. The name now **survives removing every game**. `user_id_for_username` reads `accounts` first. **Delete account** removes the row. **Before the migration:** the code works without the table — `accounts_enabled()` falls back to profile usernames and re-checks every 5 min. | `main.py` (`accounts_enabled`, `account_row`, `claim_username`, `save_profile`, `my_games`, `my_account_payload`, `delete_account`), `db/migrations/001_*.sql` |

### Medium
| ID | Status | What changed | Open part |
|---|---|---|---|
| **M01** compatibility filter bypass + GTA editions | ✅ | **Platform:** the server requires it (422) for multi-platform games, invalid values are rejected, and single-platform games get it filled in. **GTA PC** is split into `PC (Enhanced)` and `PC (Legacy)`, and each is its own crossplay group. **Minecraft edition and LoL server** are `must_match` fields. | Old rows with unknown values still pass (deliberate: "unknown never blocks"). One live GTA profile still has the old value `PC` and must pick Enhanced/Legacy on its next save. |
| **M02** 20-result cap / discovery stops / no incoming likes | 🟡 | **"Liked you" list:** `GET /api/incoming-likes`, with **Like back / Pass**. **Deck order:** players who already like you are flagged `likes_you` and sorted first. **Skips:** remembered per tab (`sessionStorage`) and sent as `exclude`; the server returns `has_more`. **End-of-deck options:** "Show more players", or "See the N players you skipped again". | Filtering still happens in Python **after** the 500+300 row window (no SQL/RPC matching yet), and `total` is still "within the window". |
| **M03** double skip | ✅ | **One swipe at a time:** `inFlight.swipe` lock and buttons disabled during the animation. **The delayed step** only applies if the game and card index are unchanged. | — |
| **M04** like / save not idempotent | 🟡 | **Likes:** a unique index `(from_user_id, to_user_id, game)` (migration 001), a duplicate-key race is treated as "already liked", and `mutual` is computed **after** the insert. **Find Matches:** locked for the whole save→match chain. | No transaction/RPC for like+mutual. |
| **M05** referral / metadata races | 🟡 | **Client:** `pm_ref` is only removed after the server accepted it. | **Server:** `referred_by` + counter are still not atomic, and the `app_metadata` read-modify-write can still lose a concurrent edit. Referrals give no reward yet, so the risk is low. |
| **M06** deletion not transactional; no way to delete without a game profile | 🟡 | **New standalone `/settings` page:** works with zero game profiles. It has account info, log out, what's public, blocked players + Unblock, and delete account. **Delete account** also deletes the `accounts` row. | Deletion is still sequential with no rollback/retry, and the "contact support" message still has no address (no domain yet). |
| **M07** JWT not restricted enough | 🟡 | `jwt.decode(..., audience="authenticated", options={"require": ["exp", "sub"]})`, plus a UUID check on `sub`. Tests cover a missing/wrong aud, missing/expired exp, a non-UUID sub and the wrong secret. | **Issuer not pinned** on purpose (the HS256 secret is project-unique). **No revocation check:** a deleted/suspended user's token works until `exp` (≤1 h). Most endpoints need a profile row, but `/api/block` doesn't. |
| **M08** DB fan-out / polling cost | 🟡 | **Polling:** one `GET /api/poll?game=&ping=1` replaces ping + squad + pending + incoming (~18 → ~6 queries per 15 s). All four views share one helper `social_state()`. **Counters:** `/api/games` is one query instead of 12; it and `/api/stats` are cached 60 s / 20 s and cleared on profile save/delete. **Indexes** on likes/profiles/blocks (migration 001). | No rate limiting, no backoff/jitter, no SQL matching. Public profile still does an auth lookup + per-game mutual counts. |
| **M09** no deadlines; upstream errors look like "not found" | 🟡 | **`auth_user()`:** returns `None` only for a real 404 (`user_not_found`); any other Auth error → **503**. **`save_profile`:** keeps the already-copied avatar if Auth is down. **Password screens:** forgot-password and save-new-password have try/catch and button locks. | No AbortController/deadline on client fetches; some public fetches still don't check `res.ok` everywhere. |
| **M10** block promise wider than reality | ✅ | **Public profile:** `GET /api/public-profile` reads an optional token; if viewer and owner blocked each other (either direction) → **404**. The profile page sends the token when logged in. **Wording:** the Block confirm, landing "Safety" and Settings texts now say exactly this: hidden from matches/likes/squads in every game; profile page still public for logged-out visitors. | Legacy public `/profile-full` and `/profile-squad` still don't know the viewer. The squad tab is only fetched after the profile itself loaded, so a blocked viewer stops at the 404. |
| **M11** report overwritable; no unmatch/unblock; no moderation | 🟡 | **Reports:** a later plain block keeps `reported=true` and the earlier reason. **Unmatch:** `DELETE /api/like` removes the likes both ways; there's a button in the squad list. **Unblock:** `GET /api/blocks` + `DELETE /api/block` in Settings; **reported players can't be unblocked (409)**. **Report UI:** an in-app dialog with reasons + details replaces `window.prompt`. | No moderation queue/tool or case status yet, and reports are still deleted when either account is deleted. |
| **M12** password recovery hijacked by the Sign-up tab | ✅ | Recovery is its own mode (`AUTH_MODE="recovery"`), the Log in / Sign up tabs are hidden, `setAuthMode` is a no-op while recovering, and the buttons lock. | — |
| **M13** accessibility | 🟡 | **Dialogs:** focus moves into them (match, game picker, report) and returns to the opener. **ARIA state:** `aria-pressed` on language pills and avatar/banner pickers; `aria-selected` + `tabpanel` on profile tabs; `aria-selected` on auth tabs. **Toasts:** `role=status aria-live=polite`. **Contrast:** `--faint` raised to `#8090a0` (≥4.5:1 on the panels). **Labels:** the password toggle label changes; the bio textarea has a label. **Decorative text:** the blurred placeholder text is hidden from screen readers. | No full focus trap / `inert` background, no arrow-key tab pattern, no screen-reader pass done. |
| **M14** reproducible release, DB invariants, tests | 🟡 | **Dependencies:** `requirements.txt` pins exact versions (+ `requirements-dev.txt`). **Tests:** a **pytest suite on an in-memory fake Supabase** (`tests/`, 46 tests) that never touches the real DB; the fake mirrors the unique constraints. **CI:** GitHub Actions (`.github/workflows/tests.yml`) runs pytest + `node --check` on every push — the first run passed. **Schema:** migration 001 is in the repo. | Transitive deps not locked. The full existing schema/RLS isn't dumped into the repo (only new migrations). Render still auto-deploys without waiting for CI (owner setting: "Auto-Deploy → After CI checks pass"). |
| **M15** launch prerequisites / headers | 🟡 | **Headers:** CSP (`default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, connect limited to self + Supabase), `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS, `Permissions-Policy`. **API:** `Cache-Control: no-store` on all `/api/*`. **SRI:** an integrity hash on supabase-js on every page. | **CSP still has `'unsafe-inline'`** for scripts (a few inline `onclick`/`onerror` handlers). Still open: Confirm email, final Terms/Privacy, support contact, rate limiting. |

### Low
| ID | Status | Notes |
|---|---|---|
| **L01** score is not a probability; `Any` not a wildcard on `same` fields | ⏸ | Unchanged. Kept as a ranking score; the country model is a deliberate decision. |
| **L02** profile tabs overflow at 320 px | ✅ | The Highlights placeholder tab was removed, so three tabs fit. |
| **L03** game / intent lost through sign-up | ✅ | **Game:** `/app?game=X` as a guest → `/?game=X` → stored → after login `/app?game=X`, and landing game cards carry their game too. | Returning to a specific *profile* after login is not implemented. |
| **L04** profile pages identical for crawlers | ✅ | `/u/<name>` is rendered with the player's name in `<title>`, description and OG/Twitter tags. Unknown players get a real **404**. |
| **L05** coming-soon sections / overpromising copy | 🟡 | **Removed:** Highlights and the disabled photo-upload button. **Copy:** "Add to squad" → **"Like"**, and "Takes 20 seconds" removed. **No contact:** squadmates without IGN/Discord show "No contact added yet", and saving a profile without either shows a nudge. | Locked Verified/Legendary badges are still shown in Achievements. |
| **L06** `test_env.py` printed the service key | ✅ | Now prints only `set` / `MISSING`. The file is local and git-ignored. |
| **L07** modal avatar / report via prompt / long names | 🟡 | **Avatar:** passed into the LIKE SENT / match modal. **Report:** now an in-app form. **Placeholder:** hidden from the accessibility tree. | Long names / IGNs on mobile modals not reworked. |

---

## B. Problems we found ourselves while fixing (please re-check too)

1. **Squad list didn't redraw after the last squadmate was removed.** This is what you saw after Block ("card stays until reload"). **Cause:** the "force redraw" reset value `""` was equal to the empty squad's signature. **Fix:** the reset value is now `null`.
2. **"Liked you" / pending could stay stale up to 15 s.** A request that had started before an action finished after it. **Fix:** refreshes are now coalesced into one request, and an action that happens mid-request triggers one more refresh after it.
3. **Account switch without logout** — covered under H01.

## C. New code to review (added after your report)

| Area | Endpoints / files |
|---|---|
| Incoming likes, unmatch | `GET /api/incoming-likes`, `DELETE /api/like?to_user=&game=` |
| One-request refresh | `GET /api/poll?game=&ping=` → `social_state()` in `main.py`; `refreshSocial()` / `applySquad()` in `ui.js` |
| Blocks list / unblock | `GET /api/blocks`, `DELETE /api/block?to_user=` (409 if reported) |
| Settings page | `/settings` → `settings.html`, `static/js/settings.js`, `static/css/settings.css` |
| Match paging | `POST /api/match` body `exclude: [...]`, response `has_more`, `likes_you` |
| Accounts | `accounts` table, `accounts_enabled()` fallback, `claim_username()` |
| Report dialog | `#report-modal` in `ui.html`, `openReport` / `sendReport` in `ui.js` |
| Profile page SSR | `profile_page()` in `main.py` (HTML-escaped title/OG, 404) |
| Tests / CI | `tests/` (fake DB in `tests/fakedb.py`), `pytest.ini`, `.github/workflows/tests.yml` |

**How to run the tests:**

```bash
pip install -r requirements-dev.txt
python -m pytest
```

They use a fake database and dummy keys, and never read the real `.env` values.

## D. Questions we'd like your opinion on

1. Is the `accounts_enabled()` fallback safe, or should it now be removed since the migration has run?
2. Is a short-lived CSP with `'unsafe-inline'` acceptable for now? Which inline handlers should go first?
3. Is anything in `/api/poll` or `social_state()` leaking contact info to non-mutual players?
4. With the new features, what are the most important missing tests?
