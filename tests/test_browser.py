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


def test_an_old_find_never_unlocks_a_half_loaded_game(open_page, users, make_profile):
    """R4-M02: Find in CS2, switch to GTA while the save is held, the old save fails: GTA's Find stays locked
    until GTA has loaded, no CS2 form is ever saved as GTA, and no old error is shown."""
    make_profile(users["alice"], "Alice")
    make_profile(users["alice"], "Alice", "gta")
    make_profile(users["bob"], "Bob")
    page = open_page("/app?game=cs2", as_user=users["alice"])
    wait_for(page, READY)
    page.evaluate("() => { __hold('/api/profile'); __hold('/api/meta/gta'); document.getElementById('btn-find-matches').click(); }")
    page.evaluate("() => { selectGame('gta'); }")
    page.evaluate("__release('/api/profile', 'fail')")
    page.wait_for_timeout(300)
    assert page.evaluate("state.game") == "gta" and page.evaluate("document.getElementById('btn-find-matches').disabled")
    page.evaluate("() => document.getElementById('profile-form')?.requestSubmit?.()")   # Enter in the old form
    page.wait_for_timeout(300)
    posts = page.evaluate("__sends.filter(s => s[0] === 'POST' && s[1].includes('/api/profile')).length")
    assert posts == 1                                                   # only the original CS2 save
    page.evaluate("__release('/api/meta/gta')")
    wait_for(page, "() => state.gameReady && !document.getElementById('btn-find-matches').disabled")
    assert page.evaluate("[...document.querySelectorAll('.toast.error')].length") == 0


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
