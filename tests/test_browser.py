"""Real-browser tests (Chromium) for the frontend flows and the request interleavings from the Codex reviews.
Setup and helpers: tests/browser_support.py. Each test gets a fresh fake DB."""
import json
import time

from browser_support import FAKE_SUPABASE_JS, base_url, browser, context, open_page, wait_for  # noqa: F401
from conftest import make_token

READY = "() => typeof state !== 'undefined' && state.game && !state.loading && !!document.getElementById('active-card')"


def uid_of(auth_header):
    try:
        import jwt
        return jwt.decode(auth_header[7:], options={"verify_signature": False})["sub"]
    except Exception:
        return ""


def record_requests(page):
    """[(method, path, uid)] for every /api request the page really sends — survives reloads."""
    sent = []
    page.on("request", lambda r: "/api/" in r.url and sent.append(
        (r.method, r.url.split("/api/")[1].split("?")[0], uid_of(r.headers.get("authorization", "")))))
    return sent


def test_app_loads_and_mutual_like_reveals_contact(open_page, users, make_profile, api, context):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobCS")
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    assert "Bob" in page.inner_text("#active-card") and "BobCS" not in page.content()   # hidden before mutual
    page.click('[data-action="like"]')
    wait_for(page, "() => document.getElementById('match-modal').classList.contains('active')")
    assert page.inner_text("#modal-title") == "IT'S A MATCH!"
    assert "BobCS" in page.inner_text("#modal-them-ign")
    assert context.errors == []


def test_pass_during_a_pending_skip_never_skips_the_next_player(open_page, users, make_profile, api, db):
    make_profile(users["alice"], "Alice")
    others = {"bob": users["bob"], "carol": users["carol"], "dave": db.auth.admin.create_user(email="dave@example.com")}
    for name, uid in others.items():
        make_profile(uid, name.title())
        api.post("/api/like", user=uid, json={"to_user": "alice", "game": "cs2"})
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    wait_for(page, "() => document.querySelectorAll('[data-like-back]').length === 3")
    order = page.evaluate("state.matches.map(m => m.username)")
    first, second = order[0], order[1]
    third = order[2]
    page.click('[data-action="skip"]')                                  # 280 ms swipe animation starts...
    assert page.evaluate("document.getElementById('active-card').classList.contains('swipe-left') && inFlight.swipe")
    page.evaluate(f"document.querySelector('[data-unmatch-user=\"{first}\"]').click()")   # ...and Pass removes it
    page.wait_for_timeout(700)
    assert page.evaluate("state.matches[state.currentMatchIndex].username") == second
    assert second not in page.evaluate("[...getSkipped()]")
    # and Skip itself still works afterwards: it moves on and remembers who was skipped
    page.click('[data-action="skip"]')
    page.wait_for_timeout(500)
    assert page.evaluate("state.matches[state.currentMatchIndex].username") == third
    assert second in page.evaluate("[...getSkipped()]")


def test_old_scan_failing_after_A_B_A_switch_is_ignored_and_rescanned(open_page, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "gta")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.evaluate("() => { __hold('/api/match'); findMatches({ keepTab: true }); }")
    page.evaluate("async () => { await selectGame('gta'); await selectGame('cs2'); }")
    before = page.evaluate("__sends.filter(s => s[1].includes('/api/match')).length")
    page.evaluate("__release('/api/match', 'fail')")
    wait_for(page, READY)
    after = page.evaluate("__sends.filter(s => s[1].includes('/api/match')).length")
    assert after > before                                               # a fresh scan for the current game ran
    assert page.evaluate("[...document.querySelectorAll('.toast.error')].length") == 0
    assert page.evaluate("state.game") == "cs2" and "Bob" in page.inner_text("#active-card")


def test_refresh_that_returns_another_account_never_sends_with_it(open_page, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    sent = record_requests(page)
    expired_a = make_token(users["alice"], exp=int(time.time()) - 60)
    token_b = make_token(users["bob"], exp=int(time.time()) + 3600)
    page.evaluate("([a, b]) => { localStorage.setItem('pm_access_token', a);"
                  " __auth.refresh = async () => ({ data: { session: { access_token: b } } }); }", [expired_a, token_b])
    with page.expect_navigation():
        page.evaluate("authFetch('/api/account', { method: 'PUT', headers: { 'Content-Type': 'application/json' },"
                      " body: JSON.stringify({ bio: 'A_PRIVATE' }) }).catch(() => {})")
    puts = [s for s in sent if s[:2] == ("PUT", "account")]
    assert puts and all(u == users["alice"] for _, _, u in puts)        # only A's (expired) token was ever used
    assert (db.users[users["bob"]].app_metadata.get("playmate") or {}).get("bio") != "A_PRIVATE"


def test_login_as_someone_else_in_another_tab_reloads_open_pages(open_page, users, make_profile, context, base_url):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    settings = open_page("/settings", as_user=users["alice"])
    settings.wait_for_function("() => document.body.innerText.toLowerCase().includes('alice')")
    app = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(app, READY)
    other_tab = context.new_page()
    other_tab.goto(base_url + "/terms")
    with settings.expect_navigation(), app.expect_navigation():
        other_tab.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["bob"], exp=int(time.time()) + 3600))
    settings.wait_for_function("() => document.body.innerText.toLowerCase().includes('bob')")
    wait_for(app, "() => typeof pageUid !== 'undefined' && pageUid === %s" % json.dumps(users["bob"]))


def test_settings_and_profile_never_act_with_another_accounts_token(open_page, users, make_profile, db):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    token_b = make_token(users["bob"], exp=int(time.time()) + 3600)
    for path, call in (("/settings", "authFetch('/api/account', { method: 'DELETE' })"),
                       ("/u/alice", "authFetch('/api/account', { method: 'PUT', body: '{}' })")):
        page = open_page(path, as_user=users["alice"])
        page.wait_for_function("() => typeof pageUid !== 'undefined' && pageUid !== ''")
        sent = record_requests(page)
        page.evaluate("t => localStorage.setItem('pm_access_token', t)", token_b)   # same tab: no storage event
        with page.expect_navigation():   # the page reloads itself as the account in storage...
            try:
                msg = page.evaluate(f"{call}.then(() => 'sent', e => e.message)")
            except Exception as e:   # ...which may destroy the context before the answer arrives
                assert "destroyed" in str(e) or "navigat" in str(e).lower(), e
                msg = "AUTH_SWITCHED"
        assert msg == "AUTH_SWITCHED"
        assert [s for s in sent if s[0] in ("PUT", "DELETE")] == []
    assert users["alice"] in db.users and users["bob"] in db.users


def test_rejected_session_at_start_keeps_the_requested_game(open_page, users, make_profile, base_url):
    make_profile(users["alice"], "Alice")
    page = open_page("/terms")
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["alice"], exp=int(time.time()) - 60))
    page.goto(base_url + "/app?game=cs2")
    page.wait_for_url("**/?game=cs2", timeout=8000)


def test_a_save_in_flight_locks_the_form_and_a_failure_keeps_the_edits(open_page, users, make_profile):
    """R4-M02 (now prevented by design) + pre-launch #4: no game switch while saving; a failed save keeps the edits,
    says so, and leaving with unsaved changes asks first."""
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "gta")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    assert page.inner_text("#save-state") == "Saved ✓" and page.text_content("#btn-find-label") == "Find Teammates"
    page.select_option("#gf-rank", "Silver")
    assert page.inner_text("#save-state") == "Unsaved changes" and page.text_content("#btn-find-label") == "Save changes"
    page.evaluate("() => { __hold('/api/profile'); document.getElementById('btn-find-matches').click(); }")
    wait_for(page, "() => state.saving && document.getElementById('form-step-1').disabled")
    page.evaluate("selectGame('gta')")   # refused while saving
    assert page.evaluate("state.game") == "cs2"
    page.evaluate("__release('/api/profile', 'fail')")
    wait_for(page, "() => !state.saving && !document.getElementById('form-step-1').disabled")
    assert page.input_value("#gf-rank") == "Silver"                       # the edit is kept
    assert "Couldn't save" in page.inner_text("#save-state")
    assert page.evaluate("__sends.filter(s => s[0] === 'POST' && s[1].includes('/api/profile')).length") == 1
    dialogs = []
    page.once("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.evaluate("selectGame('gta')")                                    # unsaved changes: asks, Cancel stays
    assert dialogs and "Discard unsaved changes" in dialogs[0] and page.evaluate("state.game") == "cs2"
    page.once("dialog", lambda d: d.accept())
    page.evaluate("selectGame('gta')")                                    # OK: switches
    wait_for(page, "() => state.game === 'gta' && state.gameReady")
    assert page.inner_text("#save-state") == "Saved ✓"


def test_clean_profile_only_scans_and_revert_is_clean(open_page, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    before = page.evaluate("__sends.filter(s => s[0] === 'POST' && s[1].includes('/api/profile')).length")
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.loading && !inFlight.find")
    assert page.evaluate("__sends.filter(s => s[0] === 'POST' && s[1].includes('/api/profile')).length") == before
    page.select_option("#gf-rank", "Silver")
    page.select_option("#gf-rank", "Gold Nova")                           # edit then revert = clean
    assert page.inner_text("#save-state") == "Saved ✓"
    page.click('.lang-pill[data-code="tr"]')
    assert page.inner_text("#save-state") == "Unsaved changes"
    page.evaluate("document.getElementById('opt-same-language').click()")   # a filter is not a saved preference
    page.click('.lang-pill[data-code="tr"]')
    assert page.inner_text("#save-state") == "Saved ✓"

def test_an_old_like_failing_shows_no_error_in_the_new_game(open_page, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "gta")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.evaluate("() => { __hold('/api/like'); handleLike(); }")
    page.evaluate("async () => { await selectGame('gta'); }")
    page.evaluate("__release('/api/like', 'fail')")
    page.wait_for_timeout(500)
    assert page.evaluate("state.game") == "gta"
    assert page.evaluate("[...document.querySelectorAll('.toast.error')].length") == 0


def test_public_squad_hides_players_blocked_with_the_viewer(open_page, users, make_profile, api):
    a, b, c = users["alice"], users["bob"], users["carol"]
    for uid, name in ((a, "Alice"), (b, "Bob"), (c, "Carol")):
        make_profile(uid, name)
    for x, y in ((a, c), (b, c)):
        for frm, to in ((x, y), (y, x)):
            api.post("/api/like", user=frm, json={"to_user": {a: "alice", b: "bob", c: "carol"}[to], "game": "cs2"})
    api.post("/api/block", user=a, json={"to_user": "bob", "game": "cs2"})
    page = open_page("/u/carol", as_user=a)
    page.click('[data-tab="squad"]')
    page.wait_for_selector(".pp-mate", timeout=5000)
    page.wait_for_timeout(300)
    names = page.locator(".pp-mate b").all_inner_texts()
    assert "Alice" in names and "Bob" not in names


# A page is "ready" when its own JS has run. Checked with plain evaluate, which works under the real CSP
# (wait_for_function needs eval, which the CSP forbids).
PAGE_READY = {
    "/": "location.pathname !== '/' || document.querySelectorAll('#lp-games > *').length > 0",
    "/app?game=cs2": "typeof state !== 'undefined' && state.gameReady === true",
    "/settings": "document.getElementById('acc-summary').textContent.toLowerCase().includes('alice')",
    "/u/alice": "!!document.querySelector('.pp-tabs')",
    "/terms": "document.body.innerText.length > 500",
    "/privacy": "document.body.innerText.length > 500 && window.scrollY > 100",   # legal.js scrolled to Privacy
}


def poll(page, js, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        if page.evaluate(js):
            return True
        time.sleep(0.1)
    raise AssertionError(f"never true: {js}")


def watch_errors(ctx):
    """Every page of this context records uncaught errors in ctx.page_errors (asserted by close_clean)."""
    ctx.page_errors = []
    ctx.on("page", lambda page: page.on("pageerror", lambda e: ctx.page_errors.append(str(e))))
    return ctx


def close_clean(ctx):
    errors = ctx.page_errors
    ctx.close()
    assert errors == [], f"uncaught page errors: {errors}"


def mobile_context(browser):
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, bypass_csp=True)
    ctx.add_init_script(FAKE_SUPABASE_JS)
    ctx.route("**/unpkg.com/**", lambda r: r.abort())
    return watch_errors(ctx)


def login(page, base_url, uid):
    page.goto(base_url + "/terms")
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(uid, exp=int(time.time()) + 3600))


def no_sideways_scroll(page, label):
    # compare with the SCREEN width: on a phone, Chromium widens innerWidth to fit wide content (then zooms out)
    overflow = page.evaluate("document.documentElement.scrollWidth") - page.viewport_size["width"]
    assert overflow <= 1, f"{label} scrolls sideways by {overflow}px"


def test_pages_fit_a_phone_screen(browser, base_url, db, users, make_profile):
    make_profile(users["alice"], "Alice")
    ctx = mobile_context(browser)
    page = ctx.new_page()
    login(page, base_url, users["alice"])
    for path, ready in PAGE_READY.items():
        page.goto(base_url + path)
        poll(page, ready)   # the real page rendered (a blank page would "fit" too)
        no_sideways_scroll(page, path)
    close_clean(ctx)


def test_populated_squad_with_longest_names_fits_a_phone(browser, base_url, db, users, make_profile, api):
    """R5-M02: 40-character unbroken IGN/Discord and a 24-character name in the mobile Squad tab must wrap."""
    long_ign, long_dc, long_name = "X" * 40, "d" * 40, "B" * 24
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], long_name, in_game_username=long_ign, discord_username=long_dc)
    api.post("/api/like", user=users["alice"], json={"to_user": long_name.lower(), "game": "cs2"})
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    ctx = mobile_context(browser)
    page = ctx.new_page()
    login(page, base_url, users["alice"])
    page.goto(base_url + "/app?game=cs2")
    poll(page, PAGE_READY["/app?game=cs2"])
    page.locator('button[data-tab="squad"]').first.click()
    poll(page, "document.body.innerText.includes('%s')" % long_ign)
    no_sideways_scroll(page, "squad tab")
    close_clean(ctx)


def test_real_csp_runs_every_page_script(browser, base_url, db, users, make_profile):
    """No CSP bypass: every page's own JS must run (readiness) and nothing may be blocked."""
    make_profile(users["alice"], "Alice")
    ctx = watch_errors(browser.new_context())
    ctx.add_init_script(FAKE_SUPABASE_JS)
    ctx.route("**/unpkg.com/**", lambda r: r.abort())
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and "Content Security Policy" in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, base_url, users["alice"])
    for path, ready in PAGE_READY.items():
        page.goto(base_url + path)
        poll(page, ready)
    assert errors == []
    ctx.close()


def test_real_supabase_sdk_loads_under_csp_and_sri(browser, base_url, db):
    """The real supabase-js from unpkg must pass the CSP and its SRI hash (needs internet, as CI has)."""
    ctx = browser.new_context()
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and ("Content Security Policy" in m.text or "integrity" in m.text)
            and errors.append(m.text))
    page.goto(base_url + "/")
    poll(page, "typeof window.supabase?.createClient === 'function'", timeout=20)
    assert errors == []
    ctx.close()


RETRY_SHOWN = "() => !!document.querySelector('[data-action=retry-load]')"


def test_failed_game_load_offers_a_retry_and_can_be_picked_again(open_page, users, make_profile):
    """R5-M03: one failed /api/meta request must not strand the game: Try again works, and so does re-picking it."""
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "gta")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.evaluate("() => { __hold('/api/meta/gta'); selectGame('gta'); }")
    page.evaluate("__release('/api/meta/gta', 'fail')")
    wait_for(page, RETRY_SHOWN)
    assert page.inner_text("#game-bar-name") == "GTA Online"   # the bar no longer claims CS2
    page.click("[data-action=retry-load]")
    wait_for(page, "() => state.game === 'gta' && state.gameReady")
    page.evaluate("async () => { await selectGame('cs2'); __hold('/api/meta/gta'); selectGame('gta'); }")
    page.evaluate("__release('/api/meta/gta', 'fail')")
    wait_for(page, RETRY_SHOWN)
    page.evaluate("selectGame('gta')")   # = picking GTA again in the game picker
    wait_for(page, "() => state.game === 'gta' && state.gameReady && !document.getElementById('btn-find-matches').disabled")


def test_looking_now_turns_off_on_screen_when_it_expires(open_page, users, make_profile):
    """R5-L01: the button follows the stored expiry without a reload."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.evaluate("() => { state.profile.looking_until = new Date(Date.now() + 1500).toISOString(); renderLookingButton(); }")
    assert "min left" in page.inner_text("#btn-looking")
    page.wait_for_timeout(17_000)   # past the expiry + one 15-second refresh
    assert "min left" not in page.inner_text("#btn-looking")
    assert not page.evaluate("document.getElementById('btn-looking').classList.contains('on')")


def test_an_old_poll_failing_shows_no_connection_warning_in_the_new_game(open_page, users, make_profile):
    """R5-L02"""
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "gta")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=gta", as_user=users["alice"])
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady")
    page.evaluate("() => { __hold('/api/poll'); refreshSquad({ fresh: true }).catch(() => {}); }")
    page.evaluate("async () => { await selectGame('cs2'); }")
    wait_for(page, READY)
    page.evaluate("__release('/api/poll', 'fail')")
    page.wait_for_timeout(300)
    assert page.evaluate("getComputedStyle(document.getElementById('net-banner')).display") == "none"


def test_settings_and_profile_refresh_returning_another_account_send_nothing_with_it(open_page, users, make_profile, db):
    """R3-H02 refresh branch: a 401, then the refreshed session belongs to another account: never sent, page reloads."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    expired_a = make_token(users["alice"], exp=int(time.time()) - 60)
    token_b = make_token(users["bob"], exp=int(time.time()) + 3600)
    for path, call in (("/settings", "authFetch('/api/account', { method: 'DELETE', body: JSON.stringify({ confirm: 'DELETE' }) })"),
                       ("/u/alice", "authFetch('/api/account', { method: 'PUT', body: JSON.stringify({ bio: 'A_PRIVATE' }) })")):
        page = open_page(path, as_user=users["alice"])
        page.wait_for_function("() => typeof pageUid !== 'undefined' && pageUid !== ''")
        sent = record_requests(page)
        page.evaluate("([a, b]) => { localStorage.setItem('pm_access_token', a);"
                      " __auth.refresh = async () => ({ data: { session: { access_token: b } } }); }", [expired_a, token_b])
        with page.expect_navigation():
            try:
                page.evaluate(f"{call}.catch(() => {{}})")
            except Exception as e:
                assert "destroyed" in str(e) or "navigat" in str(e).lower(), e
        writes = [s for s in sent if s[0] in ("PUT", "DELETE")]
        assert writes and all(u == users["alice"] for _, _, u in writes)   # only A's own (expired) token
    assert users["bob"] in db.users and (db.users[users["bob"]].app_metadata.get("playmate") or {}).get("bio") != "A_PRIVATE"


def test_rate_limited_poll_shows_no_connection_warning_but_a_real_failure_does(open_page, users, make_profile):
    """R7-L01: 429 = try again next tick (no banner); a 500 still shows the banner (positive control)."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    banner = "getComputedStyle(document.getElementById('net-banner')).display"
    page.route("**/api/poll**", lambda r: r.fulfill(status=429, headers={"Retry-After": "30"},
                                                    content_type="application/json", body='{"detail": "Too many requests."}'))
    page.evaluate("refreshSquad().catch(() => {})")
    page.wait_for_timeout(400)
    assert page.evaluate(banner) == "none"
    page.unroute("**/api/poll**")
    page.route("**/api/poll**", lambda r: r.fulfill(status=500, content_type="application/json", body='{"detail": "x"}'))
    page.evaluate("refreshSquad().catch(() => {})")
    page.wait_for_timeout(400)
    assert page.evaluate(banner) == "flex"


def test_one_way_like_is_a_light_confirmation_not_the_match_modal(open_page, users, make_profile):
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.click('[data-action="like"]')
    wait_for(page, "() => [...document.querySelectorAll('.toast')].some(t => t.textContent.includes('Like sent'))")
    assert not page.evaluate("document.getElementById('match-modal').classList.contains('active')")


def test_like_and_like_back_from_a_public_profile(open_page, users, make_profile, api):
    """Product #6: a shared profile link is actionable — Like, then (as the other player) Like back → mutual."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobCS")
    page = open_page("/u/bob", as_user=users["alice"])
    page.wait_for_selector('[data-like-game="cs2"]')
    assert "BobCS" not in page.content()
    page.click('[data-like-game="cs2"]')
    page.wait_for_selector("text=Like sent ✓")
    other = open_page("/u/alice", as_user=users["bob"])   # same browser: bob logs in in another tab → reloads
    other.wait_for_selector('[data-like-game="cs2"].hot')
    other.click('[data-like-game="cs2"]')
    other.wait_for_selector("text=In your squad")
    assert api.get("/api/poll?game=cs2", user=users["alice"])[1]["squadmates"][0]["in_game_username"] == "BobCS"


def test_profile_like_keeps_its_result_when_the_follow_up_read_fails(open_page, users, make_profile):
    """R8-M01: POST like succeeds, then GET /api/relationship 429s: the card still says sent, no second Like button."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/u/bob", as_user=users["alice"])
    page.wait_for_selector('[data-like-game="cs2"]')
    page.route("**/api/relationship**", lambda r: r.fulfill(status=429, headers={"Retry-After": "30"},
                                                            content_type="application/json", body='{"detail": "slow"}'))
    page.click('[data-like-game="cs2"]')
    page.wait_for_selector("text=Like sent ✓")
    page.wait_for_timeout(300)
    assert page.locator('[data-like-game="cs2"]').count() == 0


def test_in_your_squad_opens_the_squad_on_a_phone(browser, base_url, db, users, make_profile, api):
    """R8-L01"""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob", in_game_username="BobCS")
    api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    ctx = mobile_context(browser)
    page = ctx.new_page()
    login(page, base_url, users["alice"])
    page.goto(base_url + "/u/bob")
    page.click("text=In your squad")
    poll(page, "typeof state !== 'undefined' && state.gameReady === true")
    poll(page, "document.body.dataset.view === 'squad' && document.body.innerText.includes('BobCS')")
    assert page.locator("#squad-panel").is_visible()
    close_clean(ctx)


def test_open_profile_follows_what_the_other_player_does(open_page, users, make_profile, api):
    """R8-L02: Bob likes Alice while Alice has Bob's profile open; coming back to the tab shows Like back."""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    page = open_page("/u/bob", as_user=users["alice"])
    page.wait_for_selector('[data-like-game="cs2"]:not(.hot)')
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    page.evaluate("window.dispatchEvent(new Event('focus'))")   # = returning to this tab
    page.wait_for_selector('[data-like-game="cs2"].hot')
    api.delete("/api/like?to_user=alice&game=cs2", user=users["bob"])   # bob takes it back
    page.click('[data-tab="achievements"]')
    page.click('[data-tab="games"]')
    page.wait_for_selector('[data-like-game="cs2"]:not(.hot)')


def test_signed_in_player_without_a_profile_is_told_to_add_the_game(open_page, users, make_profile):
    """R8-L03: a brand-new account (no game profile yet) viewing someone gets the 'add this game' guidance."""
    make_profile(users["alice"], "Alice")
    page = open_page("/u/alice", as_user=users["carol"])
    page.wait_for_selector("text=Add Counter-Strike 2 to your games to like them")


def test_steam_profile_field_and_squad_link(open_page, browser, users, make_profile, api):
    """Steam games on PC offer the field; a friend code is saved as a link; the mutual squadmate gets 'Open Steam profile'."""
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "lol")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    assert page.locator("#steam-row").is_visible()
    page.fill("#steam_profile", "22202")
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.loading && !!document.getElementById('active-card')")
    assert api.get("/api/my-profile?game=cs2", user=users["alice"])[1]["steam_profile"] == "profiles/76561197960287930"
    assert page.input_value("#steam_profile") == "https://steamcommunity.com/profiles/76561197960287930"
    page.evaluate("selectGame('lol')")
    wait_for(page, "() => state.game === 'lol' && state.gameReady")
    assert not page.locator("#steam-row").is_visible()                 # LoL isn't a Steam game
    api.post("/api/like", user=users["bob"], json={"to_user": "alice", "game": "cs2"})
    api.post("/api/like", user=users["alice"], json={"to_user": "bob", "game": "cs2"})
    bob_device = watch_errors(browser.new_context(viewport={"width": 1280, "height": 860}, bypass_csp=True))
    bob_device.add_init_script(FAKE_SUPABASE_JS)
    bob_device.route("**/unpkg.com/**", lambda r: r.abort())
    bob = open_page("/app?game=cs2", as_user=users["bob"], ctx=bob_device)   # another player = another device
    bob.wait_for_selector('a.sm-btn:has-text("Open Steam profile")')
    href = bob.get_attribute('a.sm-btn:has-text("Open Steam profile")', "href")
    assert href == "https://steamcommunity.com/profiles/76561197960287930"
    assert bob.get_attribute('a.sm-btn:has-text("Open Steam profile")', "rel") == "noopener noreferrer"
    close_clean(bob_device)



def test_steam_prefill_finds_it_in_any_saved_game_and_counts_as_contact(open_page, users, make_profile):
    """R9-L02: LoL first (no Steam), CS2 second (Steam) → a new Steam game is prefilled.
    R9-L03: a Steam-only profile gets no "add a contact" reminder."""
    a = users["alice"]
    make_profile(a, "Alice", "lol")
    make_profile(a, "Alice", "cs2", steam_profile="steamcommunity.com/id/alicesteam")
    page = open_page("/app?game=cs2", as_user=a)
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady")
    page.evaluate("() => { localStorage.removeItem('playmate_shared'); state.myGames = ['lol', 'cs2']; }")   # fresh device
    page.evaluate("selectGame('helldivers2')")
    wait_for(page, "() => state.game === 'helldivers2' && state.gameReady")
    page.select_option("#platform", "PC")
    wait_for(page, "() => !document.getElementById('steam-row').hidden")
    assert page.input_value("#steam_profile") == "https://steamcommunity.com/id/alicesteam"
    # Steam-only contact: no reminder (leaving the half-filled Helldivers setup asks first: accept)
    page.once("dialog", lambda d: d.accept())
    page.evaluate("selectGame('cs2')")
    wait_for(page, "() => state.game === 'cs2' && state.gameReady")
    page.fill("#in_game_username", "")
    page.fill("#discord_username", "")
    page.click("#btn-find-matches")
    page.wait_for_timeout(800)
    toasts = page.evaluate("[...document.querySelectorAll('.toast')].map(t => t.textContent).join(' | ')")
    assert "so squadmates can reach you" not in toasts


PROFILE_POSTS = "__sends.filter(s => s[0] === 'POST' && s[1].includes('/api/profile')).length"


def fill_step1_cs2(page):
    page.select_option("#region", "middle-east")
    page.select_option("#country", "Iran")
    page.select_option("#gf-mode", "Premier")
    page.select_option("#gf-rank", "Silver")
    page.click('.lang-pill[data-code="fa"]')


def test_first_profile_is_a_two_step_setup(open_page, users, make_profile, api, db):
    """Pre-launch #1: a brand-new player gets 'How you play' → 'Connect with squadmates'; Next/Back never save;
    a taken username sends them back to step 2 with everything kept; the final save creates one profile."""
    make_profile(users["bob"], "Bob")                       # takes the name "bob"
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady && state.wizard")
    assert page.is_visible("#form-step-1") and not page.is_visible("#form-step-2")
    assert page.inner_text("#wizard-step") == "Step 1 of 2" and not page.is_visible("#btn-find-matches")
    page.click("#btn-wizard-next")                          # nothing filled: stays on step 1
    assert page.evaluate("state.step") == 1 and page.is_visible("#form-step-1")
    fill_step1_cs2(page)
    page.click("#btn-wizard-next")
    wait_for(page, "() => state.step === 2")
    assert page.is_visible("#form-step-2") and not page.is_visible("#form-step-1")
    assert page.is_visible("#username-input") and page.is_visible("#steam-row")   # CS2 on PC offers Steam
    page.click("#btn-wizard-back")
    assert page.input_value("#gf-rank") == "Silver"         # values survive Back
    page.click("#btn-wizard-next")
    assert page.evaluate(PROFILE_POSTS) == 0                # Next / Back never save
    page.fill("#username-input", "Bob")
    page.fill("#in_game_username", "AliceCS")
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.saving && state.saveError")
    assert page.evaluate("state.step") == 2 and page.evaluate("document.activeElement.id") == "username-input"
    assert page.input_value("#in_game_username") == "AliceCS" and page.evaluate("state.wizard")
    page.fill("#username-input", "Alice")
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.wizard && state.hasProfile")
    assert page.inner_text("#save-state") == "Saved ✓" and page.is_visible("#form-step-1") and page.is_visible("#form-step-2")
    assert page.evaluate(PROFILE_POSTS) == 2
    rows = [r for r in db.tables["profiles"] if r["user_id"] == users["alice"]]
    assert len(rows) == 1 and rows[0]["in_game_username"] == "AliceCS" and rows[0]["game_meta"]["fields"]["rank"] == "Silver"


def test_adding_a_game_uses_the_setup_and_optional_fields_sit_in_more_details(open_page, users, make_profile):
    make_profile(users["alice"], "Alice")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady")
    assert not page.evaluate("state.wizard")                # saved game: one form
    page.evaluate("selectGame('battlefield')")
    wait_for(page, "() => state.game === 'battlefield' && state.gameReady && state.wizard")
    assert page.is_visible("#platform-row")                 # BF: several platforms — asked
    assert page.locator("#form-step-1 #gf-class_type").count() == 0   # optional class is not in step 1...
    assert page.locator("#more-details #gf-class_type").count() == 1  # ...but under "More game details"
    page.select_option("#platform", "PC")
    page.select_option("#gf-favorite_mode", index=1)
    page.click("#btn-wizard-next")
    wait_for(page, "() => state.step === 2")
    assert not page.is_visible("#username-input")           # name already claimed
    page.click("#more-details summary")
    page.select_option("#gf-class_type", index=1)
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.wizard && state.hasProfile")
    assert page.evaluate("state.profile.fields.class_type")
    page.evaluate("selectGame('lol')")
    wait_for(page, "() => state.game === 'lol' && state.gameReady && state.wizard")
    assert not page.is_visible("#platform-row")             # LoL: PC only — not asked

def test_new_game_on_a_phone_opens_the_setup(browser, base_url, db, users, make_profile):
    ctx = mobile_context(browser)
    page = ctx.new_page()
    login(page, base_url, users["alice"])
    page.goto(base_url + "/app?game=cs2")
    poll(page, "typeof state !== 'undefined' && state.gameReady === true && state.wizard === true")
    poll(page, "document.body.dataset.view === 'profile'")
    assert page.locator("#btn-wizard-next").is_visible()
    box = page.locator("#btn-wizard-next").bounding_box()
    assert box["height"] >= 44
    no_sideways_scroll(page, "setup step 1")
    close_clean(ctx)


INTENT = "JSON.parse(sessionStorage.getItem('pm_intent') || 'null')"


def test_shared_player_is_kept_through_signup_and_setup(open_page, users, make_profile, base_url):
    """Pre-launch #3: a guest opens Bob's profile → joins → sets up CS2 → 'View @bob' brings them back to Like."""
    make_profile(users["bob"], "Bob")
    page = open_page("/u/bob")                                          # logged out
    cta = page.get_attribute(".pp-cta", "href")
    assert cta == "/?game=cs2&next=%2Fu%2Fbob" and "Bob" in page.text_content(".pp-cta")
    page.goto(base_url + cta)                                           # landing captures the intent
    assert page.evaluate(INTENT)["target"] == "bob" and page.evaluate(INTENT)["game"] == "cs2"
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["alice"], exp=int(time.time()) + 3600))
    page.goto(base_url + "/app?game=cs2")                               # = after signing up / logging in
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady && state.wizard")
    assert "save your profile" in page.inner_text("#intent-strip") and page.locator("[data-intent-go]").count() == 0
    fill_step1_cs2(page)
    page.click("#btn-wizard-next")
    page.fill("#username-input", "Alice")
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.wizard && state.hasProfile")
    page.wait_for_selector("[data-intent-go]")
    assert page.get_attribute("[data-intent-go]", "href") == "/u/bob"
    page.click("[data-intent-go]")
    page.wait_for_selector('[data-like-game="cs2"]')                    # back on Bob's profile, ready to like
    assert page.evaluate(INTENT) is None                                # used up


def test_logged_in_player_adding_the_game_keeps_the_target_and_can_dismiss(open_page, users, make_profile):
    make_profile(users["alice"], "Alice", "lol")
    make_profile(users["bob"], "Bob")
    page = open_page("/u/bob", as_user=users["alice"])
    link = page.get_attribute("text=Add Counter-Strike 2 to your games to like them", "href")
    assert link == "/app?game=cs2&next=%2Fu%2Fbob"
    page.click("text=Add Counter-Strike 2 to your games to like them")
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady && state.wizard")
    assert "next=" not in page.url                                      # removed from the address bar
    assert "@bob" in page.inner_text("#intent-strip")
    page.click("[data-intent-dismiss]")
    assert not page.is_visible("#intent-strip") and page.evaluate(INTENT) is None


def test_intent_rejects_unsafe_targets_and_other_accounts(open_page, users, make_profile, base_url):
    page = open_page("/terms")
    for bad in ("//evil.example", "https://evil.example/u/bob", "/u/bob/extra", "/u/..", "/u/...", "/u/bob%2fx",
                "/u/bob?x=1", "/u/b", "/u/" + "x" * 25, "/u/bob%0a", "/x/bob", "javascript:alert(1)"):
        page.evaluate("sessionStorage.removeItem('pm_intent')")
        page.goto(base_url + "/?next=" + __import__("urllib.parse").parse.quote(bad, safe=""))
        assert page.evaluate(INTENT) is None, bad
    # bound to the account that first saw it: another account in this tab doesn't inherit it
    make_profile(users["alice"], "Alice")
    make_profile(users["carol"], "Carol")
    page.goto(base_url + "/?game=cs2&next=%2Fu%2Fbob")
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["alice"], exp=int(time.time()) + 3600))
    page.goto(base_url + "/app?game=cs2")
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady")
    assert page.evaluate(INTENT)["uid"] == users["alice"]
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["carol"], exp=int(time.time()) + 3600))
    page.goto(base_url + "/app?game=cs2")
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady")
    assert page.evaluate(INTENT) is None and not page.is_visible("#intent-strip")


def test_match_card_shows_the_bio_safely_in_two_lines(open_page, users, make_profile, api):
    """Pre-launch #2"""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    bio = "بازیکن آروم، شب‌ها پلی میدم & \"quotes\" &amp; " + "لوله‌کش " * 40
    assert api.put("/api/account", user=users["bob"], json={"bio": bio[:280]})[0] == 200
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    el = page.locator("#active-card .card-bio")
    assert el.text_content() == bio[:280].strip()                      # escaped text, not HTML
    line = float(page.evaluate("parseFloat(getComputedStyle(document.querySelector('.card-bio')).lineHeight)"))
    assert el.bounding_box()["height"] <= line * 2 + 2                  # clamped to two lines
    assert page.locator('[data-action="like"]').is_visible()


def test_empty_state_says_why(open_page, users, make_profile, api):
    """Pre-launch #6: filters / skipped / liked / nobody compatible each get their own honest message."""
    make_profile(users["alice"], "Alice", languages="fa")
    make_profile(users["bob"], "Bob", languages="en")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.evaluate("() => { document.getElementById('opt-same-language').checked = true; findMatches({ keepTab: true }); }")
    page.wait_for_selector("text=Your filters hide everyone")
    page.click('[data-action="clear-filters"]')
    wait_for(page, READY)
    page.click('[data-action="skip"]')                                   # skip the only player → end of the list
    page.wait_for_selector("text=You've seen everyone for now")
    page.click('[data-action="reset-skipped"]')
    wait_for(page, READY)
    page.click('[data-action="like"]')
    page.wait_for_selector("text=You've liked everyone available")


def test_r11_wizard_edits_are_protected_and_enter_works(open_page, users, make_profile):
    """F1: step-1 edits count as unsaved (switching asks); F6: Enter in a text field saves on step 2;
    F7: errors are announced and tied to the fields."""
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, "() => typeof state !== 'undefined' && state.gameReady && state.wizard")
    assert page.evaluate("isDirty()") is False                      # untouched setup isn't "unsaved"
    page.click("#btn-wizard-next")                                  # nothing filled
    assert page.get_attribute("#region", "aria-invalid") == "true"
    assert "Please fill in" in page.inner_text("#form-errors")
    fill_step1_cs2(page)
    assert page.evaluate("isDirty()") is True and page.is_hidden("#form-errors")
    asked = []
    page.once("dialog", lambda d: (asked.append(d.message), d.dismiss()))
    page.evaluate("selectGame('gta')")
    assert asked and page.evaluate("state.game") == "cs2" and page.input_value("#gf-rank") == "Silver"
    page.click("#btn-wizard-next")   # (step 1 has only selects/pills: browsers never submit a form on Enter there)
    wait_for(page, "() => state.step === 2")
    page.click("#btn-wizard-back")
    assert page.evaluate("isDirty()") is True                       # still protected after Back
    page.click("#btn-wizard-next")
    page.fill("#username-input", "Alice")
    page.focus("#discord_username")
    page.keyboard.press("Enter")                                    # Enter on step 2 = Save
    wait_for(page, "() => !state.wizard && state.hasProfile")


def test_r11_equivalent_steam_is_not_a_change_and_old_errors_go(open_page, users, make_profile):
    """F8"""
    make_profile(users["alice"], "Alice", steam_profile="https://steamcommunity.com/profiles/76561197960287930")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    for same in ("76561197960287930", "22202", "steamcommunity.com/profiles/76561197960287930/"):
        page.fill("#steam_profile", same)
        assert page.inner_text("#save-state") == "Saved ✓", same
    page.select_option("#mic", "none")
    page.route("**/api/profile", lambda r: r.fulfill(status=503, content_type="application/json", body='{"detail": "x"}'))
    page.click("#btn-find-matches")
    wait_for(page, "() => !state.saving && !!state.saveError")
    assert "save" in page.inner_text("#save-state").lower()
    page.select_option("#mic", "voice")                             # back to what is saved
    assert page.inner_text("#save-state") == "Saved ✓"


def test_r11_intent_strip_is_visible_during_phone_setup(browser, base_url, db, users, make_profile):
    """F2"""
    make_profile(users["bob"], "Bob")
    ctx = mobile_context(browser)
    page = ctx.new_page()
    page.goto(base_url + "/?game=cs2&next=%2Fu%2Fbob")
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["alice"], exp=int(time.time()) + 3600))
    page.goto(base_url + "/app?game=cs2")
    poll(page, "typeof state !== 'undefined' && state.gameReady === true && state.wizard === true")
    assert page.locator("#intent-strip").is_visible() and "@bob" in page.inner_text("#intent-strip")
    page.click("#btn-wizard-next")   # empty: stays on step 1, the strip stays
    assert page.locator("#intent-strip").is_visible()
    no_sideways_scroll(page, "setup with strip")
    close_clean(ctx)


def test_r11_confirmation_link_only_carries_a_fresh_unowned_intent(open_page):
    """F3"""
    page = open_page("/?game=cs2&next=%2Fu%2Fbob")
    assert "next=%2Fu%2Fbob" in page.evaluate("intentQuery()")
    page.evaluate("() => { const i = JSON.parse(sessionStorage.getItem('pm_intent')); i.uid = 'someone-else';"
                  " sessionStorage.setItem('pm_intent', JSON.stringify(i)); }")
    assert "next=" not in page.evaluate("intentQuery()")
    assert page.evaluate("sessionStorage.getItem('pm_intent')") is None
    page.goto(page.url)
    page.evaluate("() => { const i = JSON.parse(sessionStorage.getItem('pm_intent')); i.at = Date.now() - 48 * 3600e3;"
                  " sessionStorage.setItem('pm_intent', JSON.stringify(i)); }")
    assert "next=" not in page.evaluate("intentQuery()")


def test_r11_bio_counts_emoji_as_one_character(open_page, users, make_profile):
    """F5"""
    make_profile(users["alice"], "Alice")
    page = open_page("/u/alice", as_user=users["alice"])
    page.click("#btn-edit")
    page.fill("#edit-bio", "🎮" * 300)
    assert page.evaluate("Array.from(document.getElementById('edit-bio').value).length") == 280
    assert page.inner_text("#bio-count") == "280/280"


def test_r11_match_card_fits_a_phone(browser, base_url, db, users, make_profile):
    """R1"""
    make_profile(users["alice"], "Alice")
    make_profile(users["bob"], "Bob")
    for width in (375, 320):
        ctx = browser.new_context(viewport={"width": width, "height": 812}, is_mobile=True, bypass_csp=True)
        ctx.add_init_script(FAKE_SUPABASE_JS)
        ctx.route("**/unpkg.com/**", lambda r: r.abort())
        watch_errors(ctx)
        page = ctx.new_page()
        login(page, base_url, users["alice"])
        page.goto(base_url + "/app?game=cs2")
        poll(page, "typeof state !== 'undefined' && !!document.getElementById('active-card')")
        no_sideways_scroll(page, f"match card at {width}px")
        close_clean(ctx)
