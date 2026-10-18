"""Browser tests: the real pages and JS in headless Chromium (Playwright), against the real FastAPI app running in
this process on the in-memory fake DB (tests/fakedb.py) — never the real Supabase.

supabase-js (unpkg) is blocked and replaced by a small fake (`window.__auth`) so auth events, refreshes and
logouts are deterministic. `window.__hold(pattern)` holds the next matching fetch until the test releases it,
to reproduce request interleavings with the unmodified page code.
"""
import socket
import threading
import time

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")   # browser tests need: pip install -r requirements-dev.txt && python -m playwright install chromium
import uvicorn  # noqa: E402

import main  # noqa: E402
from conftest import make_token  # noqa: E402

FAKE_SUPABASE_JS = """
window.__auth = { listeners: [], refresh: null, signOuts: 0 };
window.supabase = { createClient: () => ({ auth: {
  onAuthStateChange(cb) { __auth.listeners.push(cb); return { data: { subscription: { unsubscribe() {} } } }; },
  getSession: async () => ({ data: { session: null } }),
  refreshSession: async () => (__auth.refresh ? __auth.refresh() : { data: { session: null } }),
  signOut: async () => { __auth.signOuts++; },
  signInWithPassword: async () => ({ data: {}, error: { message: "test" } }),
}}) };
window.__sends = [];   // [method, path, uid of the bearer token]
window.__holds = [];
window.__hold = (pattern) => { const h = { pattern }; __holds.push(h); return h; };
window.__release = (pattern, how = "ok") => {
  const h = __holds.find(x => x.pattern === pattern && x.resolve);
  h.resolve(how); __holds.splice(__holds.indexOf(h), 1);
};
const realFetch = window.fetch.bind(window);
window.fetch = async (url, opts = {}) => {
  const auth = (opts.headers || {}).Authorization || "";
  let uid = "";
  try { uid = JSON.parse(atob(auth.slice(7).split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).sub; } catch {}
  __sends.push([opts.method || "GET", String(url), uid]);
  const h = __holds.find(x => !x.resolve && String(url).includes(x.pattern));
  if (h) {
    const how = await new Promise(r => { h.resolve = r; });
    if (how === "fail") throw new TypeError("Failed to fetch (held)");
  }
  return realFetch(url, opts);
};
"""


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture(scope="session")
def browser():
    with playwright_sync.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def context(browser, base_url, db):
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, bypass_csp=True)   # test helpers use eval; CSP has its own test
    ctx.add_init_script(FAKE_SUPABASE_JS)
    ctx.route("**/unpkg.com/**", lambda r: r.abort())
    ctx.route("**/*.supabase.co/**", lambda r: r.abort())
    ctx.errors = []
    yield ctx
    ctx.close()


@pytest.fixture
def open_page(context, base_url):
    """open_page(path, as_user=uid) -> page logged in as that user (token in localStorage, like after sign-in)."""
    def _open(path, as_user=None, ctx=None):
        page = (ctx or context).new_page()
        page.on("pageerror", lambda e: context.errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and "net::ERR_FAILED" not in m.text   # = the blocked unpkg/supabase
                and context.errors.append(m.text))
        if as_user:
            page.goto(base_url + "/terms")
            page.evaluate("t => localStorage.setItem('pm_access_token', t)", make_token(as_user, exp=int(time.time()) + 3600))
        page.goto(base_url + path)
        return page
    return _open


def wait_for(page, js, timeout=5000):
    page.wait_for_function(js, timeout=timeout)
