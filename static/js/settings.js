/* =========================================================
   PlayMate — account settings (/settings)
   Works without any game profile: account summary, log out, blocked players (unblock), delete account.
========================================================= */
const API = "/api";
const SUPABASE_URL = "https://fffejwdrqhizgxpjacgn.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmZmVqd2RycWhpemd4cGphY2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTExNjgsImV4cCI6MjA4MDc4NzE2OH0.Zr2And6oP8PKmCDiW3rNcimBWh5cUV22YvnWwhQQz7s";
const sb = window.supabase?.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) || null;
const $ = (id) => document.getElementById(id);

function esc(v) {
  return String(v ?? "").replace(/[&<>"'`]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;" })[ch]);
}
function toast(msg, type = "info") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  $("toast-container").appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
function token() { return localStorage.getItem("pm_access_token") || ""; }

// The account this page was opened as. Its form/buttons must never be sent with another account's token
// (logged in as someone else in another tab, or a refresh that returned another session): reload instead.
let pageUid = "";
function tokenUid(t = token()) {
  try { return JSON.parse(atob(t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).sub || ""; } catch { return ""; }
}
function accountSwitched() {
  location.reload();
  return new Error("AUTH_SWITCHED");
}
window.addEventListener("storage", (e) => {
  if (pageUid && (e.key === "pm_access_token" || e.key === null) && tokenUid() !== pageUid) location.reload();
});

async function authFetch(url, opts = {}) {
  const send = t => fetch(url, { ...opts, headers: { ...(opts.headers || {}), Authorization: `Bearer ${t}` } });
  const first = token();
  if (!pageUid) pageUid = tokenUid(first);   // the first authenticated call fixes the page's account
  else if (tokenUid(first) !== pageUid) throw accountSwitched();
  let res = await send(first);
  if (res.status === 401 && sb) {
    const { data } = await sb.auth.refreshSession().catch(() => ({ data: null }));
    const t = data?.session?.access_token;
    if (t) {
      if (tokenUid(t) !== pageUid) throw accountSwitched();
      localStorage.setItem("pm_access_token", t);
      res = await send(t);
    }
  }
  if (res.status === 401) {
    location.href = "/";
    throw new Error("AUTH");
  }
  return res;
}

async function json(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
  return data;
}

// same rule as ui.js / profile.js
function avatarSrc(id) {
  const m = /^avatar-(\d+)$/.exec(String(id || ""));
  return m ? `/static/img/avatars/${id}.${Number(m[1]) > 12 ? "webp" : "svg"}` : "";
}
function hue(name) {
  let h = 0;
  for (const ch of String(name || "").toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}
function faceHtml(name, avatar) {
  const src = avatarSrc(avatar);
  return src
    ? `<span class="avatar-face has-img set-face"><img src="${esc(src)}" alt=""></span>`
    : `<span class="avatar-face set-face" style="--hue:${hue(name)}">${esc((String(name || "?").trim()[0] || "?").toUpperCase())}</span>`;
}

function forgetDevice() {
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const k = localStorage.key(i);
    if (k && (k.startsWith("pm_") || k.startsWith("playmate_") || k.startsWith("sb-"))) localStorage.removeItem(k);
  }
  try { sessionStorage.clear(); } catch { }
}

/* ---------------- account ---------------- */
async function loadAccount() {
  try {
    const a = await json(await authFetch(`${API}/account`));
    const name = a.display_username || a.username;
    const since = a.member_since ? new Date(a.member_since).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : "";
    $("acc-summary").innerHTML = name
      ? `${faceHtml(name, a.avatar)}<div><b>${esc(name)}</b><span class="muted">${since ? "Member since " + esc(since) + " · " : ""}${a.games.length} game${a.games.length === 1 ? "" : "s"}</span></div>`
      : `<div><b>No game profile yet</b><span class="muted">Pick a game in the app to choose your PlayMate name.</span></div>`;
    if (a.username) {
      const href = `/u/${encodeURIComponent(a.username)}`;
      $("acc-profile-link").href = href;
      $("acc-profile-link").hidden = false;
      $("nav-my-profile").href = href;
    }
  } catch (e) {
    if (e.message !== "AUTH") $("acc-summary").innerHTML = `<span class="muted">Couldn't load your account. ${esc(e.message)}</span>`;
  }
}

/* ---------------- blocked players ---------------- */
async function loadBlocked() {
  try {
    const { blocked } = await json(await authFetch(`${API}/blocks`));
    $("blocked-list").innerHTML = blocked.length
      ? blocked.map(b => {
        const name = b.display_username || b.username;
        return `<div class="blocked-row">${faceHtml(name, b.avatar)}<b>${esc(name)}</b>
          ${b.reported
            ? `<span class="muted small">Reported — stays blocked</span>`
            : `<button type="button" class="btn-secondary small" data-unblock="${esc(b.username)}">Unblock</button>`}</div>`;
      }).join("")
      : `<span class="muted">You haven't blocked anyone.</span>`;
  } catch (e) {
    if (e.message !== "AUTH") $("blocked-list").innerHTML = `<span class="muted">Couldn't load blocked players.</span>`;
  }
}

async function unblock(username, btn) {
  if (!confirm(`Unblock ${username}? You can see each other in matches again.`)) return;
  btn.disabled = true;
  try {
    await json(await authFetch(`${API}/block?to_user=${encodeURIComponent(username)}`, { method: "DELETE" }));
    toast(`${username} unblocked`, "success");
    loadBlocked();
  } catch (e) {
    btn.disabled = false;
    if (e.message !== "AUTH") toast(e.message, "error");
  }
}

/* ---------------- log out / delete ---------------- */
async function logout() {
  try { await Promise.race([sb?.auth.signOut(), new Promise(r => setTimeout(r, 1500))]); } catch { }
  forgetDevice();
  location.href = "/";
}

async function deleteAccount() {
  if ($("delete-input").value.trim().toUpperCase() !== "DELETE") return;
  const btn = $("delete-go");
  btn.disabled = true;
  btn.textContent = "Deleting…";
  try {
    await json(await authFetch(`${API}/account`, {
      method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirm: "DELETE" }),
    }));
    forgetDevice();
    location.href = "/?deleted=1";
  } catch (e) {
    if (e.message !== "AUTH") toast(e.message, "error");
    btn.disabled = false;
    btn.textContent = "Delete forever";
  }
}

/* ---------------- events + init ---------------- */
document.addEventListener("click", (e) => {
  if (!(e.target instanceof Element)) return;
  const ub = e.target.closest("[data-unblock]");
  if (ub) return unblock(ub.dataset.unblock, ub);
  if (e.target.closest("#btn-logout")) return logout();
  if (e.target.closest("#delete-start")) {
    $("delete-start").hidden = true;
    $("delete-confirm").hidden = false;
    $("delete-input").focus();
    return;
  }
  if (e.target.closest("#delete-go")) return deleteAccount();
});
$("delete-input").addEventListener("input", () => {
  $("delete-go").disabled = $("delete-input").value.trim().toUpperCase() !== "DELETE";
});

(async function init() {
  if (!token()) {
    location.href = "/";
    return;
  }
  loadAccount();
  loadBlocked();
})();
