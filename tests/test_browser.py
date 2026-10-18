"""Real-browser tests (Chromium) for the frontend flows and the request interleavings from the Codex reviews.
Setup and helpers: tests/browser_support.py. Each test gets a fresh fake DB."""
import json
import time

from browser_support import base_url, browser, context, open_page, wait_for  # noqa: F401  (fixtures)
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
        try:
            msg = page.evaluate(f"{call}.then(() => 'sent', e => e.message)")
        except Exception:   # the page reloads itself while answering
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


def test_pages_fit_a_phone_screen(browser, base_url, db, users, make_profile):
    make_profile(users["alice"], "Alice")
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, bypass_csp=True)
    from browser_support import FAKE_SUPABASE_JS
    ctx.add_init_script(FAKE_SUPABASE_JS)
    ctx.route("**/unpkg.com/**", lambda r: r.abort())
    page = ctx.new_page()
    page.goto(base_url + "/terms")
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["alice"], exp=int(time.time()) + 3600))
    for path in ("/", "/app?game=cs2", "/settings", "/u/alice", "/terms"):
        page.goto(base_url + path)
        page.wait_for_timeout(600)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"{path} scrolls sideways by {overflow}px"
    ctx.close()


def test_real_csp_allows_every_page_script(browser, base_url, db, users, make_profile):
    """No bypass here: the deployed CSP must not block any of our own scripts/handlers on any page."""
    make_profile(users["alice"], "Alice")
    from browser_support import FAKE_SUPABASE_JS
    ctx = browser.new_context()
    ctx.add_init_script(FAKE_SUPABASE_JS)
    ctx.route("**/unpkg.com/**", lambda r: r.abort())
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and "Content Security Policy" in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base_url + "/terms")
    page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(users["alice"], exp=int(time.time()) + 3600))
    for path in ("/", "/app?game=cs2", "/settings", "/u/alice", "/terms", "/privacy"):
        page.goto(base_url + path)
        page.wait_for_load_state("networkidle")
    page.goto(base_url + "/app?game=cs2")
    page.wait_for_selector("#active-card, .empty-state", timeout=8000)
    assert errors == []
    ctx.close()


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
