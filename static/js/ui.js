/* =========================================================
   PlayMate — Find your squad (/app)
   Sections: config & auth · state · helpers · games · profile form ·
   matching & card · likes · squad & pending · modal · looking/block ·
   invite · realtime · mobile tabs · init
========================================================= */

const API_BASE = "/api";
const REALTIME_INTERVAL_MS = 15000;
const SHOW_COUNTS_FROM = 25;   // below this, player counts make the app look empty, so we hide them
const MIC_LABELS = { voice: "Voice", both: "Voice + Text", none: "No mic" };
const FIELD_ICONS = {
  favorite_mode: "flag", mode: "flag", class_type: "class", role: "class", rank: "trophy", tier: "trophy",
  server: "server", edition: "server", difficulty: "bolt", front: "globe", style: "bolt",
  division: "trophy", position: "class", activity: "flag",
};

/* ---------------- auth ---------------- */
const SUPABASE_URL = "https://fffejwdrqhizgxpjacgn.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmZmVqd2RycWhpemd4cGphY2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTExNjgsImV4cCI6MjA4MDc4NzE2OH0.Zr2And6oP8PKmCDiW3rNcimBWh5cUV22YvnWwhQQz7s";
const supabaseClient = window.supabase?.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) || null;

// supabase-js refreshes the session in the background; keep our copy of the token in sync.
// If the session now belongs to a different account, everything on this page belongs to the old one: reload.
supabaseClient?.auth.onAuthStateChange((event, session) => {
  if (event === "SIGNED_OUT") return clearAuthAndRedirect();
  if (!session?.access_token) return;
  if (pageUid && tokenUserId(session.access_token) !== pageUid) return accountChanged();
  localStorage.setItem("pm_access_token", session.access_token);
});

// the account this page was loaded for (set at init); never mix its form/state with another account's token
let pageUid = "";
let leaving = false;   // set when the app itself navigates away (account change, logout): no unsaved-changes prompt
function accountChanged() {
  leaving = true;
  stopRealtime();
  state.gen++;   // drop every answer that is still on its way
  location.reload();
}
// another tab logged out or logged in as someone else
window.addEventListener("storage", (e) => {
  if (!pageUid || (e.key !== "pm_access_token" && e.key !== null)) return;
  const uid = tokenUserId();
  if (!uid) clearAuthAndRedirect();
  else if (uid !== pageUid) accountChanged();
});

function getAccessToken() {
  return localStorage.getItem("pm_access_token") || "";
}

async function refreshAccessToken() {
  if (!supabaseClient) return null;
  try {
    const { data } = await supabaseClient.auth.refreshSession();
    const token = data?.session?.access_token || null;
    if (token) localStorage.setItem("pm_access_token", token);
    return token;
  } catch {
    return null;
  }
}

async function syncTokenFromSession() {
  if (!supabaseClient) return;
  try {
    const { data } = await supabaseClient.auth.getSession(); // refreshes if expired
    if (data?.session?.access_token) localStorage.setItem("pm_access_token", data.session.access_token);
  } catch { }
}

// Everything this device remembers about the signed-in account (token, name, last game, cached
// profile/shared fields, pending referral, Supabase session). Must be wiped when the account changes.
function clearAccountCache() {
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const k = localStorage.key(i);
    if (k && (k.startsWith("pm_") || k.startsWith("playmate_") || (k.startsWith("sb-") && k.endsWith("-auth-token")))) {
      localStorage.removeItem(k);
    }
  }
}

// user id (JWT "sub") of the stored token, without verifying it — only used to tell accounts apart
function tokenUserId(token = getAccessToken()) {
  try {
    return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).sub || "";
  } catch {
    return "";
  }
}

// a different account than last time on this device: forget the previous account's cached data
function ensureCacheOwner() {
  const uid = tokenUserId();
  const owner = localStorage.getItem("pm_uid");
  if (uid && owner && owner !== uid) {
    // forget the previous account's cached data, but never touch the current session itself: removing and
    // re-adding the token would let another open tab read "no token" in between and log out
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      const session = k === "pm_access_token" || (k && k.startsWith("sb-") && k.endsWith("-auth-token"));
      if (k && !session && (k.startsWith("pm_") || k.startsWith("playmate_"))) localStorage.removeItem(k);
    }
  }
  if (uid) localStorage.setItem("pm_uid", uid);
}

let loggingOut = false;
async function clearAuthAndRedirect() {
  if (loggingOut) return;
  loggingOut = true;
  leaving = true;
  stopRealtime();
  // revoke the refresh token on the server too (don't hang the logout if the network is slow)
  try {
    await Promise.race([supabaseClient?.auth.signOut(), new Promise(r => setTimeout(r, 1500))]);
  } catch { }
  const game = state.game || new URLSearchParams(location.search).get("game");
  clearAccountCache();
  try { sessionStorage.clear(); } catch { }
  window.location.href = game && /^[a-z0-9-]{2,20}$/.test(game) ? `/?game=${encodeURIComponent(game)}` : "/";
}

async function authFetch(url, options = {}) {
  const token = getAccessToken();
  if (!token) {
    clearAuthAndRedirect();
    throw new Error("AUTH_MISSING");
  }
  if (pageUid && tokenUserId(token) !== pageUid) {   // the stored token is another account's now
    accountChanged();
    throw new Error("AUTH_SWITCHED");
  }
  const send = (t) => fetch(url, { ...options, headers: { ...(options.headers || {}), Authorization: `Bearer ${t}` } });
  let res = await send(token);
  if (res.status === 401) {
    // token probably expired: refresh once and retry before logging out
    const fresh = await refreshAccessToken();
    if (fresh && pageUid && tokenUserId(fresh) !== pageUid) {   // the session became another account meanwhile
      accountChanged();
      throw new Error("AUTH_SWITCHED");
    }
    if (fresh) res = await send(fresh);
  }
  if (res.status === 401) {
    clearAuthAndRedirect();
    throw new Error("AUTH_EXPIRED");
  }
  return res;
}

async function apiJson(url, options = {}) {
  const res = await authFetch(url, options);
  let data = null;
  try { data = await res.json(); } catch { }
  if (!res.ok) {
    const err = new Error(typeof data?.detail === "string" ? data.detail : `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

function postJson(url, body) {
  return apiJson(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

/* ---------------- state ---------------- */
const state = {
  game: null,
  meta: null,
  games: [],
  myGames: [],
  username: "",
  displayName: "",
  hasProfile: false,
  profile: {},          // saved profile for the current game
  matches: [],
  currentMatchIndex: 0,
  squad: [],
  loading: false,
  gen: 0,    // bumped on every game selection (and account change): answers for an older one are dropped
  deck: 0,   // bumped on every new match list: swipe timers for an older list do nothing
  gameReady: false,   // the selected game's form + profile are loaded (no saving a half-loaded/old form)
  wizard: false,      // this game has no saved profile yet: 2-step setup (step 1 how you play, step 2 contact)
  step: 1,
  baseline: null,     // the saved profile as formSnapshot() — null = not saved yet
  saving: false,
  saveError: "",
};
const isCurrent = (gen) => gen === state.gen;

const inFlight = { match: false, like: false, swipe: false, find: false };

/* the player whose shared profile brought this person here (pre-launch #3): tab-scoped, bound to the account,
   24 h, only a valid username — shown until they open that profile or dismiss it */
const INTENT_TTL = 24 * 3600 * 1000;
const TARGET_RE = /^[a-z0-9_.-]{3,24}$/;
function validTargetName(v) {
  const t = String(v || "").toLowerCase();
  return TARGET_RE.test(t) && !/^\.+$/.test(t) ? t : "";
}
function readIntent() {
  let i = null;
  try { i = JSON.parse(sessionStorage.getItem("pm_intent") || "null"); } catch { }
  const fresh = i && validTargetName(i.target) && Date.now() - Number(i.at || 0) < INTENT_TTL;
  if (!fresh || (i.uid && i.uid !== pageUid) || (state.username && i.target === state.username)) {
    clearIntent();
    return null;
  }
  if (!i.uid && pageUid) {   // first seen by this account: it belongs to it now
    i.uid = pageUid;
    try { sessionStorage.setItem("pm_intent", JSON.stringify(i)); } catch { }
  }
  if (i.game && !state.games.some(g => g.id === i.game)) i.game = "";
  return i;
}
function clearIntent() {
  try { sessionStorage.removeItem("pm_intent"); } catch { }
  const el = $("intent-strip");
  if (el) { el.hidden = true; el.innerHTML = ""; }
}
// /app?next=/u/<name> (a logged-in player coming from a profile): same as the landing page's capture
function captureIntentFromUrl() {
  const url = new URL(location.href);
  const m = /^\/u\/([A-Za-z0-9_.-]{3,24})$/.exec(url.searchParams.get("next") || "");
  if (m && validTargetName(m[1])) {
    const g = url.searchParams.get("game");
    try {
      sessionStorage.setItem("pm_intent", JSON.stringify({ target: m[1].toLowerCase(), game: g && /^[a-z0-9-]{2,20}$/.test(g) ? g : "", at: Date.now() }));
    } catch { }
  }
  if (url.searchParams.has("next")) {
    url.searchParams.delete("next");
    history.replaceState(null, "", url);
  }
}
function renderIntent() {
  const el = $("intent-strip");
  const i = readIntent();
  if (!i) return;
  const name = esc(i.target);
  const gameName = esc(gameInfo(i.game)?.name || "");
  const needsSetup = !state.hasProfile && (!i.game || i.game === state.game);
  el.innerHTML = `
    <span class="intent-text">${needsSetup
      ? `You came to team up with <b>@${name}</b>${gameName ? ` in ${gameName}` : ""} — save your profile, then you can like them.`
      : `You came to team up with <b>@${name}</b>${gameName ? ` in ${gameName}` : ""}.`}</span>
    ${needsSetup ? "" : `<a class="btn-primary intent-go" href="/u/${encodeURIComponent(i.target)}" data-intent-go>View @${name} →</a>`}
    <button type="button" class="intent-close" data-intent-dismiss aria-label="Dismiss">×</button>`;
  el.hidden = false;
}

/* players skipped this session, per game — "Show more" asks the server for the ones after them */
function skippedKey(game) { return `pm_skipped:${game}`; }
function getSkipped(game = state.game) {
  try { return new Set(JSON.parse(sessionStorage.getItem(skippedKey(game)) || "[]")); } catch { return new Set(); }
}
function addSkipped(username, game = state.game) {
  const s = getSkipped(game);
  s.add(String(username).toLowerCase());
  try { sessionStorage.setItem(skippedKey(game), JSON.stringify([...s].slice(-1000))); } catch { }
}
function clearSkipped(game = state.game) {
  try { sessionStorage.removeItem(skippedKey(game)); } catch { }
}
const announced = new Set();   // squadmates we already showed a match modal for (per game: "game:user")
let inviteLoaded = false;
let realtimeTimer = null;
let lastSquadSignature = null;   // null = "redraw on the next refresh" ("" is a real value: the empty squad)
let lastSquadUsernames = new Set();
let squadBootstrapped = false;

const $ = (id) => document.getElementById(id);
const els = {
  form: $("profile-form"),
  status: $("profile-status"),
  langContainer: $("lang-container"),
  gameFields: $("game-fields"),
  cardWrapper: $("card-wrapper"),
  squadList: $("squad-list"),
  pendingSection: $("pending-section"),
  incomingSection: $("incoming-section"),
  incomingList: $("incoming-list"),
  incomingCount: $("incoming-count"),
  pendingList: $("pending-list"),
  pendingCount: $("pending-count"),
  modal: $("match-modal"),
  gameModal: $("game-modal"),
  region: $("region"),
  country: $("country"),
  city: $("city"),
  platform: $("platform"),
  mic: $("mic"),
  ign: $("in_game_username"),
  discord: $("discord_username"),
  steam: $("steam_profile"),
  steamRow: $("steam-row"),
  usernameRow: $("username-row"),
  usernameInput: $("username-input"),
  btnLooking: $("btn-looking"),
  btnFind: $("btn-find-matches"),
  optSameLang: $("opt-same-language"),
  optLookingOnly: $("opt-looking-only"),
  gameFieldsOptional: $("game-fields-optional"),
  step1: $("form-step-1"),
  step2: $("form-step-2"),
  wizardHead: $("wizard-head"),
  btnNext: $("btn-wizard-next"),
  btnBack: $("btn-wizard-back"),
  saveState: $("save-state"),
};

/* ---------------- helpers ---------------- */
function esc(value) {
  return String(value ?? "").replace(/[&<>"'`]/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;"
  })[ch]);
}

function initialOf(name) {
  return name ? String(name).trim().substring(0, 1).toUpperCase() || "?" : "?";
}

function getInitials(name) {
  return esc(initialOf(name));
}

function avatarHue(name) {
  let h = 0;
  for (const ch of String(name || "").toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

// avatar-1..12 are SVG art, avatar-13 and up illustrated WebP (same rule as profile.js)
function avatarSrc(id) {
  const m = /^avatar-(\d+)$/.exec(String(id || ""));
  return m ? `/static/img/avatars/${id}.${Number(m[1]) > 12 ? "webp" : "svg"}` : "";
}

// Chosen avatar picture, or the coloured initial when the player has none
function paintAvatar(el, name, avatar) {
  if (!el) return;
  const src = avatarSrc(avatar);
  el.classList.toggle("has-img", !!src);
  el.style.setProperty("--hue", avatarHue(name));
  if (src) el.innerHTML = `<img src="${esc(src)}" alt="">`;
  else el.textContent = initialOf(name);
}

// same thing as an HTML string, for list/card templates
function avatarInner(name, avatar) {
  const src = avatarSrc(avatar);
  return src ? `<img src="${esc(src)}" alt="" loading="lazy">` : getInitials(name);
}
function avatarClass(avatar) {
  return avatarSrc(avatar) ? " has-img" : "";
}

function svgIcon(id) {
  return `<svg class="icon"><use href="#i-${id}"/></svg>`;
}

function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  $("toast-container").appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

function showNetError() { $("net-banner").style.display = "flex"; }
function hideNetError() { $("net-banner").style.display = "none"; }

function regionLabel(id) {
  return (state.meta?.regions || []).find(r => r.id === id)?.label || id || "";
}

function langLabels(codes) {
  const map = Object.fromEntries((state.meta?.languages || []).map(l => [l.code, l.label]));
  return String(codes || "").split(",").map(c => c.trim()).filter(Boolean).map(c => map[c] || c).join(", ");
}

function gameInfo(id) {
  return state.games.find(g => g.id === id) || null;
}

function presenceOf(lastActiveIso) {
  const t = lastActiveIso ? new Date(lastActiveIso).getTime() : NaN;
  if (!Number.isFinite(t)) return "offline";
  const sec = (Date.now() - t) / 1000;
  if (sec <= 60) return "online";
  if (sec <= 600) return "away";
  return "offline";
}

function formatLastSeen(lastActiveIso) {
  const t = lastActiveIso ? new Date(lastActiveIso).getTime() : NaN;
  if (!Number.isFinite(t)) return "Last seen: unknown";
  const sec = Math.floor((Date.now() - t) / 1000);
  if (sec <= 60) return "Online";
  const min = Math.floor(sec / 60);
  if (min < 60) return `Last seen ${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `Last seen ${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `Last seen ${day}d ago`;
  if (day >= 365) return `Last seen ${Math.floor(day / 365)}y ago`;
  return `Last seen ${Math.floor(day / 30)}mo ago`;
}

async function copyText(text, label) {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`${label} copied`, "success");
  } catch {
    showToast(`${label}: ${text}`, "info");
  }
}

function fillSelect(select, options, placeholder) {
  select.innerHTML = "";
  if (placeholder) select.add(new Option(placeholder, ""));
  options.forEach(o => {
    const opt = typeof o === "string" ? new Option(o, o) : new Option(o.label, o.value);
    select.add(opt);
  });
}

/* ---------------- identity ---------------- */
function setIdentity(display) {
  const d = (display || "").trim();
  if (!d) return;
  state.displayName = d;
  state.username = d.toLowerCase();
  localStorage.setItem("pm_username", d);

  $("pm-username-display").textContent = d;
  paintAvatar($("me-avatar"), d, state.myAvatar);
  paintAvatar($("me-chip-avatar"), d, state.myAvatar);
  $("me-chip-name").textContent = d;

  const href = "/u/" + encodeURIComponent(state.username);
  ["view-profile-link", "nav-profile", "me-chip"].forEach(id => { if ($(id)) $(id).href = href; });
  $("view-profile-link").style.display = "";
  els.usernameRow.style.display = "none";
}

/* =========================================================
   GAMES
========================================================= */
async function loadGames() {
  const res = await fetch(`${API_BASE}/games`);
  state.games = (await res.json()).games || [];
}

async function loadMyGames() {
  try {
    const d = await apiJson(`${API_BASE}/my-games`);
    state.myGames = d.games || [];
    if (d.display_username) setIdentity(d.display_username);
  } catch {
    state.myGames = [];
  }
}

function renderGamePicker() {
  const grid = $("game-grid");
  grid.innerHTML = state.games.map(g => {
    const mine = state.myGames.includes(g.id);
    const current = g.id === state.game;
    return `
      <button type="button" class="game-card ${current ? "current" : ""}" data-game="${esc(g.id)}" style="--accent:${esc(g.accent)}" aria-label="${esc(g.name)}">
        <img src="${esc(g.cover)}" alt="" loading="lazy" data-fallback="${esc(g.art || "/static/img/games/default.svg")}">
        ${g.players >= SHOW_COUNTS_FROM ? `<span class="game-card-body"><span class="game-card-meta">${g.players} players</span></span>` : ""}
        ${mine ? `<span class="game-card-tag">${current ? "Playing" : "Added"}</span>` : ""}
      </button>`;
  }).join("");
}

function openGamePicker(firstTime = false) {
  renderGamePicker();
  $("game-modal-title").textContent = firstTime ? "Pick your first game" : "Choose your game";
  $("game-modal-close").style.display = firstTime && !state.game ? "none" : "";
  rememberFocus(els.gameModal);
  els.gameModal.classList.add("active");
  (els.gameModal.querySelector(".game-card.current") || els.gameModal.querySelector(".game-card"))?.focus();
}

function closeGamePicker() {
  if (!state.game) return; // must pick one first
  els.gameModal.classList.remove("active");
  restoreFocus(els.gameModal);
}

// dialogs: move focus into them, and give it back to whatever opened them
function rememberFocus(dialog) {
  dialog._returnFocus = document.activeElement;
}
function restoreFocus(dialog) {
  const el = dialog._returnFocus;
  dialog._returnFocus = null;
  if (el && document.contains(el)) el.focus?.();
}

function renderGameChrome() {
  const g = gameInfo(state.game);
  if (!g) return;
  $("game-chip-icon").src = g.icon;
  $("game-chip-name").textContent = g.name;
  $("game-chip-state").textContent = state.hasProfile ? "Active · tap to switch" : "New profile · tap to switch";
  document.documentElement.style.setProperty("--game-accent", g.accent);

  $("game-bar").style.display = "";
  $("game-bar-cover").onerror = function () { this.onerror = null; this.src = g.art; };
  $("game-bar-cover").src = g.cover;
  $("game-bar-name").textContent = g.name;
  document.title = `PlayMate | ${g.name}`;
}

async function refreshStats() {
  if (!state.game) return;
  const gen = state.gen, game = state.game;
  try {
    const region = state.profile.region || els.region.value || "";
    const res = await fetch(`${API_BASE}/stats?game=${encodeURIComponent(game)}&region=${encodeURIComponent(region)}`);
    if (!res.ok) return;
    const s = await res.json();
    if (!isCurrent(gen)) return;
    const parts = [];
    if (s.players >= SHOW_COUNTS_FROM) {
      parts.push(`${s.players} players`);
      if (region && s.in_region) parts.push(`${s.in_region} in ${regionLabel(region)}`);
    }
    if (s.looking_now > 0) parts.push(`${s.looking_now} looking now`);
    if (!parts.length) parts.push(`${gameInfo(state.game)?.genre || "Squad finder"} · Early access`);
    $("game-bar-stats").textContent = parts.join(" · ");
    state.stats = s;
  } catch { }
}

async function selectGame(gameId) {
  if (!gameId) return;
  const sameGame = gameId === state.game;
  if (els.gameModal.classList.contains("active")) {
    els.gameModal.classList.remove("active");
    els.gameModal._returnFocus = null;
  }
  if (sameGame && state.gameReady) return;   // not ready yet (still loading, or loading failed): load it again
  if (state.saving) return showToast("Saving your profile — one moment", "info");
  if (!sameGame && isDirty() && !confirm(`Discard unsaved changes to your ${gameInfo(state.game)?.name || ""} profile?`)) return;

  stopRealtime();
  const gen = ++state.gen;
  state.deck++;   // old swipe/like timers must not move the new game's list
  state.game = gameId;
  state.hasProfile = false;
  state.gameReady = false;
  state.wizard = false;
  state.baseline = null;
  state.saveError = "";
  state.profile = {};
  els.btnFind.disabled = true;   // no saving a half-loaded form; re-enabled once this game is ready
  localStorage.setItem("pm_game", gameId);
  const url = new URL(location.href);
  url.searchParams.set("game", gameId);
  history.replaceState(null, "", url);
  renderGameChrome();   // the bar shows the game being loaded, not the previous one

  // reset per-game state
  state.matches = [];
  state.currentMatchIndex = 0;
  state.squad = [];
  lastSquadSignature = null;
  lastSquadUsernames = new Set();
  squadBootstrapped = false;
    state.loadFailed = false;
  renderSquadList();
  renderPendingList([]);
  state.incomingLoaded = false;
  renderIncomingList([]);

  let meta;
  try {
    const res = await fetch(`${API_BASE}/meta/${encodeURIComponent(gameId)}`);
    if (!res.ok) throw new Error("meta");
    meta = await res.json();
  } catch {
    if (!isCurrent(gen)) return;
    state.loadFailed = true;
    els.cardWrapper.innerHTML = `<div class="empty-state"><h3>Couldn't load ${esc(gameInfo(gameId)?.name || "this game")}</h3>
      <p>Check your connection and try again.</p>
      <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="retry-load">Try again</button></div></div>`;
    return;
  }
  if (!isCurrent(gen)) return;   // switched again while loading
  state.meta = meta;

  buildForm();
  await loadProfileForGame(gen);
  if (!isCurrent(gen)) return;
  if (state.loadFailed) return;   // keep the "Couldn't load — Try again" message on screen
  state.gameReady = true;
  els.btnFind.disabled = false;
  renderWizard();
  renderIntent();
  if (state.wizard && window.innerWidth <= 760) setTab("profile");   // new game on a phone: start the setup
  renderGameChrome();
  refreshStats();
  renderIdleCenter();

  if (state.hasProfile) {
    startRealtime();
    refreshSquad().catch(() => { });
    refreshPending();
    refreshIncoming();
    // returning player: show matches straight away instead of making them press Save & Find Teammates
    findMatches({ keepTab: true });
  }
}

/* =========================================================
   PROFILE FORM
========================================================= */
function buildForm() {
  const m = state.meta;

  fillSelect(els.region, m.regions.map(r => ({ value: r.id, label: r.label })), "Select region…");
  fillSelect(els.country, [], "Select country…");
  els.country.disabled = true;
  fillSelect(els.city, [], "Optional — skip or select…");
  els.city.disabled = true;
  fillSelect(els.platform, m.platforms, m.platforms.length > 1 ? "Select platform…" : null);
  $("platform-row").hidden = m.platforms.length <= 1;   // one choice: nothing to ask (the value is still sent)
  updateSteamRow();
  $("ign-label").textContent = m.ign_label || "In-game name";
  els.ign.placeholder = `Your ${m.ign_label || "in-game name"}`;

  const fieldRow = f => `
    <div class="field-row">
      <label class="field-label" for="gf-${esc(f.id)}">${svgIcon(FIELD_ICONS[f.id] || "class")}${esc(f.label)}</label>
      <select id="gf-${esc(f.id)}" data-field="${esc(f.id)}" ${f.required ? "required" : ""}>
        <option value="">${f.required ? "Select…" : "Optional — skip or select…"}</option>
        ${f.options.map(o => `<option value="${esc(o)}">${esc(o)}</option>`).join("")}
      </select>
    </div>`;
  els.gameFields.innerHTML = m.fields.filter(f => f.required).map(fieldRow).join("");
  els.gameFieldsOptional.innerHTML = m.fields.filter(f => !f.required).map(fieldRow).join("");

  if (m.crossplay_note) {
    els.gameFields.insertAdjacentHTML("beforeend", `<p class="crossplay-note">${svgIcon("globe")}${esc(m.crossplay_note)}</p>`);
  }

  els.langContainer.innerHTML = "";
  m.languages.forEach(l => {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "lang-pill";
    pill.setAttribute("aria-pressed", "false");
    pill.dataset.code = l.code;
    pill.textContent = l.label;
    pill.addEventListener("click", () => {
      const on = pill.classList.toggle("active");
      pill.setAttribute("aria-pressed", String(on));
      renderSaveState();
    });
    els.langContainer.appendChild(pill);
  });
}

// Region → Country → City (city optional). A region with one country picks it automatically.
function fillCountries(regionId, selected) {
  const r = (state.meta?.regions || []).find(x => x.id === regionId);
  const countries = r?.countries || [];
  fillSelect(els.country, countries.map(c => c.name), "Select country…");
  els.country.disabled = !r;
  if (selected && countries.some(c => c.name === selected)) els.country.value = selected;
  else if (countries.length === 1) els.country.value = countries[0].name;
}

function fillCities(regionId, countryName, selected) {
  const r = (state.meta?.regions || []).find(x => x.id === regionId);
  const c = r?.countries?.find(x => x.name === countryName);
  fillSelect(els.city, c ? c.cities : [], "Optional — skip or select…");
  els.city.disabled = !c;
  if (selected) els.city.value = selected;
}

function selectedLanguages() {
  return [...els.langContainer.querySelectorAll(".lang-pill.active")].map(p => p.dataset.code);
}

function applyProfileToForm(p) {
  els.region.value = p.region || "";
  fillCountries(p.region, p.country);
  fillCities(p.region, els.country.value, p.city);
  if (p.platform && [...els.platform.options].some(o => o.value === p.platform)) els.platform.value = p.platform;
  els.mic.value = p.mic || "voice";
  const langs = new Set(String(p.languages || "").split(",").map(s => s.trim()).filter(Boolean));
  els.langContainer.querySelectorAll(".lang-pill").forEach(pill => {
    const on = langs.has(pill.dataset.code);
    pill.classList.toggle("active", on);
    pill.setAttribute("aria-pressed", String(on));
  });
  els.ign.value = p.in_game_username || "";
  els.discord.value = p.discord_username || "";
  els.steam.value = p.steam_profile ? `https://steamcommunity.com/${p.steam_profile}` : "";
  updateSteamRow();
  const fields = p.fields || {};
  els.form.querySelectorAll("select[data-field]").forEach(s => { s.value = fields[s.dataset.field] || ""; });
}

async function loadProfileForGame(gen = state.gen) {
  const game = state.game;
  state.hasProfile = false;
  state.profile = {};
  try {
    const p = await apiJson(`${API_BASE}/my-profile?game=${encodeURIComponent(game)}`);
    if (!isCurrent(gen)) return;   // stale: another game (or the same one again) was picked meanwhile
    state.profile = p;
    if (p.avatar) state.myAvatar = p.avatar;
    state.hasProfile = true;
    setIdentity(p.display_username || p.username);
    applyProfileToForm(p);
    els.status.textContent = "";
    state.wizard = false;
    state.baseline = formSnapshot();   // what is saved = what the form shows now
  } catch (e) {
    if (!isCurrent(gen)) return;
    if (e.status !== 404) {
      state.loadFailed = true;
      els.btnFind.disabled = true;
      els.cardWrapper.innerHTML = `<div class="empty-state"><h3>Couldn't load your profile</h3>
        <p>Check your connection and try again.</p>
        <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="retry-load">Try again</button></div></div>`;
      return;
    }
    // new game: prefill what is shared between games (from another game profile, else the local cache —
    // only if that cache belongs to this account)
    let shared = {};
    try {
      const cached = JSON.parse(localStorage.getItem("playmate_shared") || "{}");
      if (cached.uid && cached.uid === tokenUserId()) shared = cached;
    } catch { }
    const others = state.myGames.filter(g => g !== game);
    if (others.length) {
      try {
        const o = await apiJson(`${API_BASE}/my-profile?game=${encodeURIComponent(others[0])}`);
        shared = { region: o.region, country: o.country, city: o.city, mic: o.mic, languages: o.languages, discord_username: o.discord_username,
                   steam_profile: o.steam_profile || shared.steam_profile };
        setIdentity(o.display_username || o.username);
        // Steam is one account across games: if the first game has none (e.g. LoL), look at the other games
        for (const g of others.slice(1)) {
          if (shared.steam_profile || !isCurrent(gen)) break;
          if (!gameInfo(g)?.steam) continue;
          const og = await apiJson(`${API_BASE}/my-profile?game=${encodeURIComponent(g)}`).catch(() => null);
          if (og?.steam_profile) shared.steam_profile = og.steam_profile;
        }
      } catch { }
      if (!isCurrent(gen)) return;
    }
    applyProfileToForm({ ...shared, in_game_username: "", fields: {} });
    state.wizard = true;   // no profile for this game yet: the short 2-step setup
    state.step = 1;
    state.baseline = null;
    els.status.textContent = `New ${gameInfo(state.game)?.name || ""} profile — fill in the game details and hit Save & Find Teammates.`;
  }
  if (!state.username) {
    const pending = (localStorage.getItem("pm_username") || "").trim();
    els.usernameRow.style.display = "";
    els.usernameInput.value = pending;
    $("pm-username-display").textContent = pending || "New player";
    paintAvatar($("me-avatar"), pending || "?");
  }
  renderLookingButton();
}

/* ---- saved / unsaved state and the 2-step first setup ---- */
// the saved preferences in one canonical string: filters, Looking now and UI state are not part of it
function formSnapshot() {
  const p = collectProfile();
  const fields = Object.keys(p.fields).sort().reduce((o, k) => (o[k] = p.fields[k], o), {});
  return JSON.stringify([p.region || "", p.country || "", p.city || "", p.platform || "", p.mic || "",
    String(p.languages || "").split(",").filter(Boolean).sort().join(","), p.in_game_username || "",
    p.discord_username || "", p.steam_profile || "", fields]);
}
function isDirty() {
  if (!state.gameReady || state.loadFailed) return false;
  return state.baseline === null ? state.wizard && state.step === 2 : formSnapshot() !== state.baseline;
}
function setSaved() {
  state.baseline = formSnapshot();
  state.saveError = "";
  renderSaveState();
}
function renderSaveState() {
  if (!state.gameReady) { els.saveState.textContent = ""; return; }
  const dirty = isDirty();
  let text = "", cls = "";
  if (state.saving) text = "Saving…";
  else if (state.saveError) { text = state.saveError; cls = "error"; }
  else if (state.wizard) text = state.step === 2 ? "Not saved yet" : "";
  else if (dirty) { text = "Unsaved changes"; cls = "dirty"; }
  else if (state.hasProfile) { text = "Saved ✓"; cls = "saved"; }
  els.saveState.textContent = text;
  els.saveState.className = `save-state ${cls}`;
  $("btn-find-label").textContent = state.wizard ? "Save & Find Teammates" : dirty ? "Save changes" : "Find Teammates";
  els.btnFind.classList.toggle("is-dirty", !state.wizard && dirty);
}
function renderWizard() {
  const w = state.wizard;
  els.wizardHead.hidden = !w;
  els.step1.hidden = w && state.step !== 1;
  els.step2.hidden = w && state.step !== 2;
  $("match-options").hidden = w && state.step === 1;
  els.btnNext.hidden = !(w && state.step === 1);
  els.btnBack.hidden = !(w && state.step === 2);
  els.btnFind.hidden = w && state.step === 1;
  $("username-hint").hidden = !(w && els.usernameRow.style.display !== "none");
  if (w) {
    $("wizard-title").textContent = state.step === 1 ? "How you play" : "Connect with squadmates";
    $("wizard-step").textContent = `Step ${state.step} of 2`;
    $("wizard-bar-fill").style.width = state.step === 1 ? "50%" : "100%";
    els.status.textContent = "";
  }
  renderSaveState();
}
function goToStep(step) {
  state.step = step;
  renderWizard();
  if (window.innerWidth <= 760) setTab("profile");
  $("wizard-title").focus({ preventScroll: true });
  els.wizardHead.scrollIntoView({ block: "start" });
}
function stepOf(el) { return el && els.step1.contains(el) ? 1 : 2; }
function wizardNext() {
  const missing = validateProfile(collectProfile()).filter(m => stepOf(m.el) === 1);
  if (missing.length) {
    markMissing(missing);
    showToast(`Please fill in: ${missing.map(m => m.label).join(", ")}`, "error");
    return;
  }
  goToStep(2);
}

// the Steam profile link is offered for Steam games played on PC (same rule as the server: games.offers_steam)
function previousShared() {
  try {
    const c = JSON.parse(localStorage.getItem("playmate_shared") || "{}");
    return c.uid && c.uid === tokenUserId() ? c : {};
  } catch { return {}; }
}

function updateSteamRow() {
  els.steamRow.hidden = !(state.meta?.steam && String(els.platform.value || "").startsWith("PC"));
}

// "id/name" or "profiles/7656…" (validated by the server) → the link squadmates open
function steamUrl(path) {
  return /^(id|profiles)\/[A-Za-z0-9_-]+$/.test(path || "") ? `https://steamcommunity.com/${path}` : "";
}

function collectProfile() {
  const fields = {};
  els.form.querySelectorAll("select[data-field]").forEach(s => { if (s.value) fields[s.dataset.field] = s.value; });
  return {
    username: state.displayName || els.usernameInput.value.trim(),
    game: state.game,
    region: els.region.value,
    country: els.country.value || null,
    city: els.city.value || null,
    platform: els.platform.value || null,
    mic: els.mic.value,
    languages: selectedLanguages().join(","),
    in_game_username: els.ign.value.trim() || null,
    discord_username: els.discord.value.trim() || null,
    steam_profile: els.steamRow.hidden ? null : (els.steam.value.trim() || null),
    fields,
  };
}

// returns [{ label, el }] for every required value that is missing, in form order
function validateProfile(p) {
  const missing = [];
  if (!p.username) missing.push({ label: "Username", el: els.usernameInput });
  if (!p.region) missing.push({ label: "Region", el: els.region });
  if (!p.country) missing.push({ label: "Country", el: els.country });
  if (state.meta?.platforms?.length > 1 && !p.platform) missing.push({ label: "Platform", el: els.platform });
  (state.meta?.fields || []).forEach(f => {
    if (f.required && !p.fields[f.id]) missing.push({ label: f.label, el: $(`gf-${f.id}`) });
  });
  if (!p.languages) missing.push({ label: "Languages", el: els.langContainer });
  return missing;
}

function markMissing(missing) {
  document.querySelectorAll(".field-invalid").forEach(el => el.classList.remove("field-invalid"));
  missing.forEach(m => m.el?.classList.add("field-invalid"));
  const first = missing[0]?.el;
  if (!first) return;
  if (window.innerWidth <= 760) setTab("profile");
  first.scrollIntoView({ behavior: "smooth", block: "center" });
  if (first.focus && first !== els.langContainer) first.focus({ preventScroll: true });
}

// clear the red outline as soon as the user fixes a field
document.addEventListener("click", (e) => {
  if (!(e.target instanceof Element)) return;
  if (e.target.closest("[data-intent-dismiss]")) clearIntent();
  else if (e.target.closest("[data-intent-go]")) { try { sessionStorage.removeItem("pm_intent"); } catch { } }
});
document.addEventListener("change", (e) => e.target.classList?.remove("field-invalid"));
document.addEventListener("input", (e) => e.target.classList?.remove("field-invalid"));
document.addEventListener("click", (e) => {
  if (e.target.closest?.(".lang-pill")) els.langContainer.classList.remove("field-invalid");
});

async function saveProfile() {
  if (!state.gameReady && !state.loadFailed) throw new Error("STALE");   // e.g. Enter pressed while a game loads
  if (state.loadFailed) {
    showToast("Your profile didn't load — tap Try again first", "error");
    throw new Error("Validation");
  }
  const payload = collectProfile();
  const missing = validateProfile(payload);
  if (missing.length) {
    if (state.wizard) goToStep(stepOf(missing[0].el));
    markMissing(missing);
    showToast(`Please fill in: ${missing.map(m => m.label).join(", ")}`, "error");
    throw new Error("Validation");
  }
  const gen = state.gen;
  state.saving = true;
  state.saveError = "";
  els.step1.disabled = els.step2.disabled = els.btnNext.disabled = els.btnBack.disabled = true;
  renderSaveState();
  try {
    const d = await postJson(`${API_BASE}/profile`, payload);
    if (!isCurrent(gen)) throw new Error("STALE");   // saved for the previous game; this page moved on
    const saved = d.data || {};
    state.hasProfile = true;
    state.profile = {
      ...state.profile, ...payload,
      username: saved.username, display_username: saved.display_username,
      looking_until: state.profile.looking_until || null,
    };
    if (!state.myGames.includes(state.game)) state.myGames.push(state.game);
    setIdentity(saved.display_username || saved.username);
    localStorage.setItem("playmate_shared", JSON.stringify({
      uid: tokenUserId(),
      region: payload.region, country: payload.country, city: payload.city, mic: payload.mic, languages: payload.languages,
      discord_username: payload.discord_username,
      // a game without Steam (LoL, console…) doesn't erase it; clearing it on a Steam game does
      steam_profile: els.steamRow.hidden ? (previousShared().steam_profile || null) : (saved.steam_profile || null),
    }));
    if (saved.steam_profile !== undefined) els.steam.value = saved.steam_profile ? steamUrl(saved.steam_profile) : "";
    state.saving = false;
    state.wizard = false;
    renderWizard();
    setSaved();   // the baseline is what the server stored (e.g. the canonical Steam link)
    renderIntent();   // "save your profile first" → "View @name"
    els.status.textContent = "";
    if (!payload.in_game_username && !payload.discord_username && !saved.steam_profile) {
      const steamToo = els.steamRow.hidden ? "" : ", Discord or Steam profile";
      showToast(`Tip: add your ${state.meta?.ign_label || "in-game name"}${steamToo || " or Discord"} so squadmates can reach you`, "info");
    }
    renderGameChrome();
    renderLookingButton();
    startRealtime();
    await captureReferral();
    refreshInvite();
  } catch (e) {
    els.step1.disabled = els.step2.disabled = els.btnNext.disabled = els.btnBack.disabled = false;   // focusable again
    if (isCurrent(gen) && e.message !== "STALE" && !String(e.message).startsWith("AUTH")) {
      showToast(e.message || "Failed to save profile", "error");
      state.saveError = "Couldn't save — your changes are kept.";
      if (/username/i.test(e.message || "") && state.wizard) {   // name taken: back to it, nothing else lost
        goToStep(2);
        markMissing([{ label: "Username", el: els.usernameInput }]);
      } else if (/Steam profile/.test(e.message || "")) {
        markMissing([{ label: "Steam profile", el: els.steam }]);
      }
    }
    throw e;
  } finally {
    state.saving = false;
    els.step1.disabled = els.step2.disabled = els.btnNext.disabled = els.btnBack.disabled = false;
    if (isCurrent(gen)) renderSaveState();
  }
}

/* =========================================================
   MATCHING & CARD
========================================================= */
function setLoading(isLoading, message = "Scanning for players…") {
  state.loading = !!isLoading;
  els.btnFind.disabled = !!isLoading;
  if (isLoading) {
    els.cardWrapper.innerHTML = `
      <div class="empty-state">
        <div class="scan-pulse"></div>
        <h3>${esc(message)}</h3>
        <p>Finding players that fit how you play…</p>
      </div>`;
  }
}

function renderIdleCenter() {
  if (!state.game) return;
  const g = gameInfo(state.game);
  els.cardWrapper.innerHTML = state.hasProfile
    ? `<div class="empty-state">
        <img class="empty-cover" src="${esc(g?.cover || "")}" alt="" data-fallback="${esc(g?.art || "/static/img/games/default.svg")}">
        <h3>Ready when you are</h3>
        <p>Hit <b>Save & Find Teammates</b> to see ${esc(g?.name || "")} players who fit how you play.</p>
        <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="find">Find Teammates</button></div>
      </div>`
    : `<div class="empty-state">
        <img class="empty-cover" src="${esc(g?.cover || "")}" alt="" data-fallback="${esc(g?.art || "/static/img/games/default.svg")}">
        <h3>Set up your ${esc(g?.name || "")} profile</h3>
        <p>Fill in the form — region, game details and languages — then hit <b>Save & Find Teammates</b>.</p>
        <div class="mobile-only" style="margin-top:16px;"><button class="btn-primary" type="button" data-action="edit-profile">Set up profile</button></div>
      </div>`;
}

// an honest empty state: say WHY there is nobody, from the server's counts (pre-launch #6)
function renderNoMatches(total, pool = {}) {
  const gameName = esc(gameInfo(state.game)?.name || "");
  if (state.hasMore) {
    els.cardWrapper.innerHTML = `
    <div class="empty-state">
      <h3>That's this batch</h3>
      <p>There are more ${gameName} players to see.</p>
      <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="more">Show more players</button></div>
    </div>`;
    return;
  }
  const n = (k) => Number(pool[k] || 0);
  const plural = (c, w) => `${c} ${w}${c === 1 ? "" : "s"}`;
  let title, text, primary;
  if (n("filtered")) {
    title = "Your filters hide everyone";
    text = `${plural(n("filtered"), "player")} would show up without "Same language only" / "Only players looking now".`;
    primary = `<button class="btn-primary" type="button" data-action="clear-filters">Show everyone</button>`;
  } else if (n("skipped")) {
    title = "You've seen everyone for now";
    text = `You skipped ${plural(n("skipped"), "player")} this session — you can look at them again.`;
    primary = `<button class="btn-primary" type="button" data-action="reset-skipped">See the ${plural(n("skipped"), "player")} you skipped</button>`;
  } else if (n("liked")) {
    title = "You've liked everyone available";
    text = `When one of the ${plural(n("liked"), "player")} you liked likes you back, they appear in your Squad with their contact.`;
    primary = `<button class="btn-primary" type="button" data-action="find">Scan again</button>`;
  } else if (n("incompatible")) {
    title = "No one you can team up with yet";
    text = `The ${gameName} players here so far play on a platform, edition or server that can't play with yours. New players join every day.`;
    primary = `<button class="btn-primary" type="button" data-action="find">Scan again</button>`;
  } else {
    title = `You're one of the first ${gameName} players here`;
    text = "PlayMate is in early access — every new player makes matches better.";
    primary = `<button class="btn-primary" type="button" data-action="find">Scan again</button>`;
  }
  els.cardWrapper.innerHTML = `
    <div class="empty-state wide">
      <h3>${title}</h3>
      <p>${text}</p>
      <div style="margin-top:16px;">${primary}</div>
      <div class="empty-actions">
        <button class="empty-action" type="button" data-action="looking">${svgIcon("bolt")}<span><b>Turn on "Looking now"</b><br>Others see you first for 1 hour</span></button>
        <button class="empty-action" type="button" data-action="invite">${svgIcon("link")}<span><b>Invite friends</b><br>Copy your invite link</span></button>
      </div>
    </div>`;
}

async function findMatches({ keepTab = false } = {}) {
  if (state.loading || inFlight.match || !state.game) return;
  inFlight.match = true;
  const game = state.game, gen = state.gen;
  if (!keepTab && window.innerWidth <= 760) setTab("match");   // results (and errors) are shown on the Match tab
  try {
    setLoading(true);
    const data = await postJson(`${API_BASE}/match`, {
      game,
      same_language_only: els.optSameLang.checked,
      looking_only: els.optLookingOnly.checked,
      exclude: [...getSkipped(game)],
    });
    if (!isCurrent(gen)) { state.loading = false; return; }   // switched game while loading: `finally` scans the new one
    state.hasMore = !!data.has_more;
    state.deck++;
    state.matches = data.matches || [];
    state.currentMatchIndex = 0;
    setLoading(false);
    await refreshStats();
    if (!isCurrent(gen)) return;
    if (!state.matches.length) return renderNoMatches(data.total, data.pool);
    renderCard();
  } catch (e) {
    if (!isCurrent(gen)) { state.loading = false; return; }   // an old game's failure: leave the new game's screen alone
    setLoading(false);
    if (e.status === 404) {
      renderIdleCenter();
      showToast("Save your profile first", "error");
    } else if (!String(e.message).startsWith("AUTH")) {
      showNetError();
      renderIdleCenter();
      showToast(e.message || "Could not fetch matches", "error");
    }
  } finally {
    inFlight.match = false;
    // the player switched game mid-scan (even A→B→A): load the current game's matches instead
    if (!isCurrent(gen) && state.hasProfile) findMatches({ keepTab: true });
  }
}

function renderCard() {
  if (state.loading) return;
  if (state.currentMatchIndex >= state.matches.length) {
    // end of this list: "more" if the server has more, otherwise ask it why there's nobody left (honest empty state)
    if (state.hasMore) return renderNoMatches(state.matches.length);
    return void findMatches({ keepTab: true });
  }

  const match = state.matches[state.currentMatchIndex];
  const p = match.profile || {};
  const name = p.display_username || match.username;
  const pct = Math.max(0, Math.min(100, Number(match.match_percent) || 0));
  const circ = 2 * Math.PI * 34;
  const langs = langLabels(p.languages);
  const remaining = state.matches.length - state.currentMatchIndex;
  const fields = p.fields || {};
  const fieldPills = (state.meta?.fields || [])
    .filter(f => fields[f.id])
    .map(f => `<span class="info-pill">${svgIcon(FIELD_ICONS[f.id] || "class")}${esc(f.label)}: <b>${esc(fields[f.id])}</b></span>`)
    .join("");
  const reasonsOpen = window.innerHeight >= 800 && window.innerWidth > 760 ? "open" : "";

  els.cardWrapper.innerHTML = `
<div class="card-stack">
  <div class="match-card" id="active-card">
    <div class="card-avatar"><div class="avatar-face${avatarClass(p.avatar)}" style="--hue:${avatarHue(name)}">${avatarInner(name, p.avatar)}</div></div>

    <div class="match-percent" title="Match score">
      <svg viewBox="0 0 80 80">
        <circle class="ring-bg" cx="40" cy="40" r="34" fill="none" stroke-width="6"/>
        <circle class="ring-fg" cx="40" cy="40" r="34" fill="none" stroke-width="6"
          stroke-dasharray="${circ}" stroke-dashoffset="${circ * (1 - pct / 100)}"/>
      </svg>
      <div class="pct-label"><span class="pct-value">${pct}%</span><span class="pct-text">MATCH</span></div>
    </div>

    <a class="card-brand" href="/u/${encodeURIComponent(match.username)}" target="_blank" rel="noopener" title="View profile"><svg><use href="#i-logo"/></svg>View profile</a>
    <div class="player-name">${esc(name)}</div>
    ${p.bio ? `<p class="card-bio" title="${esc(p.bio)}">${esc(p.bio)}</p>` : ""}
    ${match.looking_now ? '<div style="margin-top:8px;"><span class="looking-badge">● Looking for a squad now</span></div>' : ""}
    ${match.likes_you ? '<div style="margin-top:8px;"><span class="likes-you-badge">💚 Already likes you</span></div>' : ""}

    <div class="pill-container">
      <span class="info-pill">${svgIcon("globe")}<b>${esc(regionLabel(p.region))}</b>${p.city || p.country ? ` · ${esc([p.city, p.country].filter(Boolean).join(", "))}` : ""}</span>
      ${fieldPills}
      <span class="info-pill">${svgIcon("mic")}Mic: <b>${esc(MIC_LABELS[p.mic] || p.mic || "—")}</b></span>
      ${p.platform ? `<span class="info-pill">${svgIcon("monitor")}<b>${esc(p.platform)}</b></span>` : ""}
      ${langs ? `<span class="info-pill">${svgIcon("chat")}<b>${esc(langs)}</b></span>` : ""}
    </div>

    <details class="match-reasons" ${reasonsOpen}>
      <summary>Why this match</summary>
      <ul>${(match.reasons || []).map(r => `<li>${esc(r)}</li>`).join("") || "<li>New player in your game</li>"}</ul>
    </details>

    <div class="ign-row">
      <div class="ign-label">${esc(state.meta?.ign_label || "In-game name")}</div>
      <div class="ign-hidden">HIDDEN UNTIL MUTUAL LIKE</div>
    </div>
  </div>
</div>

<div class="actions">
  <div class="action-wrap">
    <button class="action-btn btn-skip" type="button" data-action="skip" aria-label="Skip" title="Skip (←)">${svgIcon("x")}</button>
    Skip
  </div>
  <div class="action-wrap">
    <button class="action-btn btn-like" type="button" data-action="like" aria-label="Like" title="Like (→) — you match when they like you too">${svgIcon("heart")}</button>
    Like
  </div>
</div>

<div class="card-safety">
  <button type="button" data-block-user="${esc(match.username)}">Block</button>
  ·
  <button type="button" data-report-user="${esc(match.username)}">Report</button>
</div>
<div class="deck-counter">${remaining} player${remaining === 1 ? "" : "s"} left in this scan</div>`;
}

function handleSkip() {
  if (state.loading || inFlight.like || inFlight.swipe) return;
  const card = $("active-card");
  if (!card) return;
  inFlight.swipe = true;
  const game = state.game, deck = state.deck;
  const index = state.currentMatchIndex;
  card.classList.add("swipe-left");
  document.querySelectorAll(".action-btn").forEach(b => b.disabled = true);
  const skippedUser = state.matches[index]?.username;
  setTimeout(() => {
    inFlight.swipe = false;
    // the list changed meanwhile (new game/scan, or this card was removed by Pass/Block): leave it alone
    if (!skippedUser || state.deck !== deck || state.matches[state.currentMatchIndex]?.username !== skippedUser) return;
    addSkipped(skippedUser, game);
    state.currentMatchIndex++;
    renderCard();
  }, 280);
}

/* =========================================================
   LIKES
========================================================= */
async function handleLike() {
  if (state.loading || inFlight.like || inFlight.swipe) return;
  const matchUser = state.matches[state.currentMatchIndex];
  if (!matchUser) return;
  inFlight.like = true;
  const game = state.game, gen = state.gen, deck = state.deck;

  const card = $("active-card");
  const buttons = document.querySelectorAll(".action-btn");
  buttons.forEach(b => b.disabled = true);
  if (card) card.classList.add("swipe-right");
  let liked = true;

  try {
    const data = await postJson(`${API_BASE}/like`, { to_user: matchUser.username, game });
    if (!isCurrent(gen)) return;   // switched game while the like was in flight
    const isMutual = data?.mutual === true || data?.status === "mutual";
    const mp = matchUser.profile || {};
    const mate = {
      username: matchUser.username, display_username: mp.display_username || matchUser.username,
      avatar: mp.avatar || "", in_game_username: null,
    };

    if (isMutual) {
      // the in-game name is only revealed by the squad endpoint
      const key = (matchUser.username || "").toLowerCase();
      announced.add(`${game}:${key}`);
      try { await refreshSquad(); } catch { }
      if (!isCurrent(gen)) return;
      const fromSquad = (state.squad || []).find(m => (m.username || "").toLowerCase() === key);
      if (fromSquad?.in_game_username) mate.in_game_username = fromSquad.in_game_username;
      if (fromSquad?.steam_profile) mate.steam_profile = fromSquad.steam_profile;
      triggerMatchModal(mate, { kind: "match" });
    } else {
      // one-way like: a light confirmation; the big modal is for a real (mutual) match
      showToast(`Like sent to ${mate.display_username} — you'll match if they like you back`, "success");
      refreshSquad().catch(() => { });
    }
    refreshPending();
  } catch (e) {
    liked = false;
    if (isCurrent(gen) && !String(e.message).startsWith("AUTH")) showToast(e.message || "Could not send like", "error");
  } finally {
    setTimeout(() => {
      if (state.deck !== deck || state.matches[state.currentMatchIndex]?.username !== matchUser.username) {
        // the deck changed meanwhile (other game / new scan): leave it alone
      } else if (liked) {
        state.currentMatchIndex++;
        renderCard();
      } else {
        card?.classList.remove("swipe-right");
        buttons.forEach(b => b.disabled = false);
      }
      inFlight.like = false;
    }, 300);
  }
}

/* =========================================================
   SQUAD & PENDING
========================================================= */
function computeSquadSignature(squad) {
  return (squad || [])
    .map(m => `${(m.username || "").toLowerCase()}|${m.in_game_username || ""}|${m.discord_username || ""}|${m.steam_profile || ""}|${m.looking_now ? 1 : 0}|${m.last_active || ""}`)
    .sort()
    .join(";");
}

/* Squad, pending likes and "Liked you" all come from one /api/poll request.
   A plain call made while a request is running just joins it. A {fresh:true} call (after the user changed
   something) can't use an answer that was asked for before the change: it queues ONE follow-up request and
   resolves only when that one has been applied. */
const social = { promise: null, gen: -1, follow: null, followPing: false };

function refreshSocial({ ping = false, fresh = false } = {}) {
  if (!state.game || !state.hasProfile) return Promise.resolve();
  if (social.promise && social.gen === state.gen) {
    if (!fresh && !ping) return social.promise;
    social.followPing = social.followPing || ping;
    if (!social.follow) {
      const running = social.promise;
      social.follow = running.catch(() => { }).then(() => {
        const p = social.followPing;
        social.follow = null;
        social.followPing = false;
        return startSocial(p);
      });
    }
    return social.follow;
  }
  return startSocial(ping);
}

function startSocial(ping) {
  if (!state.game || !state.hasProfile) return Promise.resolve();
  const game = state.game, gen = state.gen;
  social.gen = gen;
  const run = (async () => {
    const res = await authFetch(`${API_BASE}/poll?game=${encodeURIComponent(game)}${ping ? "&ping=1" : ""}`);
    if (!isCurrent(gen)) return;            // user switched game meanwhile
    if (res.status === 404) {
      applySquad(game, []);
      renderPendingList([]);
      renderIncomingList([]);
      return;
    }
    if (!res.ok) {
      const err = new Error(`poll failed: ${res.status}`);
      err.status = res.status;   // 429 = rate limited: the next tick tries again, no "connection issue" banner
      throw err;
    }
    const d = await res.json();
    if (!isCurrent(gen)) return;
    hideNetError();
    applySquad(game, d.squadmates || []);
    renderPendingList(d.pending || []);
    renderIncomingList(d.incoming || []);
  })();

  const p = run
    .catch(err => {
      console.error("Refresh failed", err);
      // an old game's poll, or a rate limit (429: the next tick simply tries again): no "connection issue" banner
      if (isCurrent(gen) && err.status !== 429 && !String(err.message).startsWith("AUTH")) showNetError();
      throw err;
    })
    .finally(() => {
      if (social.promise === p) social.promise = null;   // done: the next call starts a new request
    });
  social.promise = p;
  return p;
}

// squad changed? redraw it, and show the match modal for squadmates that just appeared
function applySquad(game, newSquad) {
  const newSet = new Set(newSquad.map(m => (m.username || "").toLowerCase()).filter(Boolean));
  const newlyAdded = [...newSet].filter(u => !lastSquadUsernames.has(u) && !announced.has(`${game}:${u}`));
  lastSquadUsernames = newSet;
  newSet.forEach(u => announced.add(`${game}:${u}`));

  // first successful refresh = baseline (no auto modal for existing squadmates)
  const wasBootstrapped = squadBootstrapped;
  squadBootstrapped = true;

  const sig = computeSquadSignature(newSquad);
  if (sig === lastSquadSignature) return;
  lastSquadSignature = sig;
  state.squad = newSquad;
  renderSquadList();

  if (wasBootstrapped && newlyAdded.length) {
    const mate = newSquad.find(m => (m.username || "").toLowerCase() === newlyAdded[0]);
    if (mate) {
      triggerMatchModal({
        username: mate.username,
        display_username: mate.display_username || mate.username,
        avatar: mate.avatar || "",
        in_game_username: mate.in_game_username,
      });
      notifyBackgroundMatch(mate.display_username || mate.username);
      if (window.innerWidth <= 760) $("tab-squad-dot").hidden = false;
    }
  }
}

// Kept as names for the call sites — all three are the same request now. Callers always run refreshSquad()
// first after a change (fresh), so the other two just join that request instead of starting another one.
function refreshSquad() { return refreshSocial({ fresh: true }); }
function refreshPending() { refreshSocial().catch(() => { }); }
function refreshIncoming() { refreshSocial().catch(() => { }); }

function renderSquadList() {
  $("squad-count").textContent = state.squad?.length ? `(${state.squad.length})` : "";
  if (!state.squad?.length) {
    els.squadList.innerHTML = `<div class="squad-empty">No squadmates yet. When you and another player both like each other, they show up here with their ${esc(state.meta?.ign_label || "in-game name")}.</div>`;
    return;
  }
  els.squadList.innerHTML = state.squad.map(mate => {
    const presence = presenceOf(mate.last_active);
    const label = formatLastSeen(mate.last_active);
    const status = mate.looking_now ? "online" : presence;
    const statusText = mate.looking_now
      ? "Looking for a squad"
      : presence === "online" ? "Online" : presence === "away" ? "Away · " + label.replace("Last seen ", "") : label;
    const ign = mate.in_game_username || "";
    const discord = mate.discord_username || "";
    const steam = steamUrl(mate.steam_profile);
    const name = mate.display_username || mate.username || "";
    return `
      <div class="squad-member">
        <span class="status-dot ${status}"></span>
        <a class="sm-avatar avatar-face${avatarClass(mate.avatar)}" href="/u/${encodeURIComponent(mate.username)}" target="_blank" rel="noopener" style="--hue:${avatarHue(name)}">${avatarInner(name, mate.avatar)}</a>
        <div class="sm-info">
          <a class="sm-name" href="/u/${encodeURIComponent(mate.username)}" target="_blank" rel="noopener">${esc(name)}</a>
          <span class="sm-status ${status}">${esc(statusText)}</span>
          ${ign || discord || steam
      ? `<span class="sm-ign">${ign ? `${esc(state.meta?.ign_label || "In-game")}: <b>${esc(ign)}</b>` : ""}${ign && discord ? "<br>" : ""}${discord ? `Discord: <b>${esc(discord)}</b>` : ""}</span>`
      : `<span class="sm-ign muted">No contact added yet — check back soon</span>`}
          <div class="sm-actions">
            ${steam ? `<a class="sm-btn primary" href="${esc(steam)}" target="_blank" rel="noopener noreferrer">Open Steam profile ↗</a>` : ""}
            ${ign ? `<button type="button" class="sm-btn" data-copy="${esc(ign)}" data-copy-label="${esc(state.meta?.ign_label || "In-game name")}">Copy ${esc(state.meta?.ign_label || "name")}</button>` : ""}
            ${discord ? `<button type="button" class="sm-btn" data-copy="${esc(discord)}" data-copy-label="Discord">Copy Discord</button>` : ""}
            <button type="button" class="sm-btn" data-unmatch-user="${esc(mate.username)}">Unmatch</button>
            <button type="button" class="sm-btn danger" data-block-user="${esc(mate.username)}">Block</button>
          </div>
        </div>
      </div>`;
  }).join("");
}

function renderIncomingList(list) {
  const known = state.incomingNames || new Set();
  state.incomingNames = new Set(list.map(p => (p.username || "").toLowerCase()));
  els.incomingSection.hidden = !list.length;
  els.incomingCount.textContent = String(list.length);
  // new like while on the Match tab (phone): dot on the Squad tab
  const hasNew = list.some(p => !known.has((p.username || "").toLowerCase()));
  if (hasNew && state.incomingLoaded && window.innerWidth <= 760) $("tab-squad-dot").hidden = false;
  state.incomingLoaded = true;
  els.incomingList.innerHTML = list.map(p => {
    const name = p.display_username || p.username || "";
    const where = [p.city, p.country].filter(Boolean).join(", ");
    return `
      <div class="squad-member incoming">
        <a class="sm-avatar avatar-face${avatarClass(p.avatar)}" href="/u/${encodeURIComponent(p.username)}" target="_blank" rel="noopener" style="--hue:${avatarHue(name)}">${avatarInner(name, p.avatar)}</a>
        <div class="sm-info">
          <a class="sm-name" href="/u/${encodeURIComponent(p.username)}" target="_blank" rel="noopener">${esc(name)}</a>
          <span class="sm-status">${p.looking_now ? "Looking for a squad now" : "Likes you"}${where ? " · " + esc(where) : ""}</span>
          <div class="sm-actions">
            <button type="button" class="sm-btn primary" data-like-back="${esc(p.username)}">💚 Like back</button>
            <button type="button" class="sm-btn" data-unmatch-user="${esc(p.username)}" data-unmatch-kind="decline">Pass</button>
          </div>
        </div>
      </div>`;
  }).join("");
}

// take one player out of the current card list (after Like back, Pass, Unmatch, Block)
function removeFromDeck(username) {
  const key = String(username).toLowerCase();
  const before = state.matches.length;
  state.matches = state.matches.filter((m, i) => {
    const drop = (m.username || "").toLowerCase() === key;
    if (drop && i < state.currentMatchIndex) state.currentMatchIndex--;
    return !drop;
  });
  if (state.matches.length !== before && $("active-card")) renderCard();
}

async function likeBack(username, btn) {
  if (inFlight.like) return;
  inFlight.like = true;
  if (btn) btn.disabled = true;
  const game = state.game, gen = state.gen;
  const key = String(username).toLowerCase();
  try {
    const data = await postJson(`${API_BASE}/like`, { to_user: username, game });
    if (!isCurrent(gen)) return;
    removeFromDeck(username);   // they're no longer a card to swipe
    announced.add(`${game}:${key}`);
    try { await refreshSquad(); } catch { }
    if (!isCurrent(gen)) return;
    const mate = (state.squad || []).find(m => (m.username || "").toLowerCase() === key);
    if (data?.mutual && mate) triggerMatchModal(mate, { kind: "match" });
    refreshIncoming();
    refreshPending();
  } catch (e) {
    if (btn) btn.disabled = false;
    if (isCurrent(gen) && !String(e.message).startsWith("AUTH")) showToast(e.message || "Could not like back", "error");
  } finally {
    inFlight.like = false;
  }
}

async function unmatchPlayer(username, kind) {
  const decline = kind === "decline";
  if (!decline && !confirm(`Unmatch ${username}? You'll leave each other's squad in ${gameInfo(state.game)?.name || "this game"} and your contact info is hidden again.`)) return;
  const game = state.game, gen = state.gen;
  try {
    await apiJson(`${API_BASE}/like?to_user=${encodeURIComponent(username)}&game=${encodeURIComponent(game)}`, { method: "DELETE" });
    if (!isCurrent(gen)) return;
    addSkipped(username, game);   // don't bring them straight back as a card
    removeFromDeck(username);
    showToast(decline ? "Passed" : "Unmatched", "success");
    lastSquadSignature = null;
    refreshSquad().catch(() => { });
    refreshIncoming();
    refreshPending();
  } catch (e) {
    if (isCurrent(gen) && !String(e.message).startsWith("AUTH")) showToast(e.message || "Could not unmatch", "error");
  }
}

function renderPendingList(list) {
  if (!list.length) {
    els.pendingSection.style.display = "none";
    els.pendingList.innerHTML = "";
    return;
  }
  els.pendingSection.style.display = "";
  els.pendingCount.textContent = String(list.length);
  els.pendingList.innerHTML = list.map(p => {
    const name = p.display_username || p.username || "";
    return `
      <div class="squad-member pending">
        <div class="sm-avatar avatar-face${avatarClass(p.avatar)}" style="--hue:${avatarHue(name)}">${avatarInner(name, p.avatar)}</div>
        <div class="sm-info">
          <span class="sm-name">${esc(name)}</span>
          <span class="sm-status">Waiting for them to like you back</span>
        </div>
      </div>`;
  }).join("");
}

/* =========================================================
   MATCH MODAL
========================================================= */
function triggerMatchModal(mate, opts = {}) {
  const kind = opts.kind || "match";
  const meName = state.displayName || "You";
  const mateName = mate?.display_username || mate?.username || "Player";
  const ignLabel = state.meta?.ign_label || "In-game";
  const meIGN = state.profile.in_game_username || els.ign.value || "—";
  const mateIGN = mate?.in_game_username || (kind === "like" ? "Hidden until match" : "—");

  $("modal-title").textContent = kind === "like" ? "LIKE SENT" : "IT'S A MATCH!";
  $("modal-sub").innerHTML = kind === "like"
    ? `You liked <b class="hl">${esc(mateName)}</b>. If they like you back, you'll match.`
    : `You're now squadmates with <b class="hl">${esc(mateName)}</b>!`;

  paintAvatar($("modal-me-avatar"), meName, state.myAvatar);
  paintAvatar($("modal-them-avatar"), mateName, mate?.avatar);
  $("modal-me-name").textContent = meName;
  $("modal-me-ign").textContent = `${ignLabel}: ${meIGN}`;
  $("modal-them-name-2").textContent = mateName;
  $("modal-them-ign").textContent = `${ignLabel}: ${mateIGN}`;
  const steamLink = $("modal-them-steam"), mateSteam = steamUrl(mate?.steam_profile);
  steamLink.hidden = !mateSteam;
  if (mateSteam) steamLink.href = mateSteam;

  els.modal.classList.toggle("is-like", kind === "like");
  if (!els.modal.classList.contains("active")) rememberFocus(els.modal);
  els.modal.classList.add("active");
  els.modal.querySelector(".btn-keep-matching")?.focus();
}

function closeModal() {
  els.modal.classList.remove("active");
  restoreFocus(els.modal);
}

function goToSquad() {
  closeModal();
  if (window.innerWidth <= 760) return setTab("squad");
  $("squad-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}
window.closeModal = closeModal;
window.goToSquad = goToSquad;

/* =========================================================
   LOOKING NOW · BLOCK / REPORT
========================================================= */
// keep the countdown (and its end) up to date without a reload; the server stays the source of truth
setInterval(() => { if (state.hasProfile && state.profile.looking_until) renderLookingButton(); }, 15000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && state.hasProfile) renderLookingButton();
});

function renderLookingButton() {
  const btn = els.btnLooking;
  const until = state.profile.looking_until ? new Date(state.profile.looking_until).getTime() : 0;
  const on = until > Date.now();
  btn.style.display = state.hasProfile ? "" : "none";
  btn.classList.toggle("on", on);
  btn.textContent = on
    ? `🟢 Looking for a squad · ${Math.max(1, Math.round((until - Date.now()) / 60000))} min left (tap to stop)`
    : "🟢 I'm looking for a squad now";
}

async function toggleLooking() {
  if (!state.hasProfile) return showToast("Save your profile first", "error");
  const until = state.profile.looking_until ? new Date(state.profile.looking_until).getTime() : 0;
  const turningOn = !(until > Date.now());
  // ask once, so we can tell them about matches while they're in another tab
  if (turningOn && "Notification" in window && Notification.permission === "default") {
    Notification.requestPermission().catch(() => { });
  }
  const game = state.game, gen = state.gen;
  try {
    const d = await postJson(`${API_BASE}/looking`, { minutes: turningOn ? 60 : 0, game });
    if (!isCurrent(gen)) return;
    state.profile.looking_until = d.looking_until;
    renderLookingButton();
    refreshStats();
    showToast(turningOn ? "You're shown as looking for 1 hour" : "Stopped looking", "success");
  } catch (e) {
    if (isCurrent(gen) && !String(e.message).startsWith("AUTH")) showToast(e.message || "Could not update your status", "error");
  }
}

function openReport(username) {
  const m = $("report-modal");
  m.dataset.user = username;
  $("report-name").textContent = username;
  $("report-details").value = "";
  m.querySelectorAll("[data-reason]").forEach(b => b.setAttribute("aria-checked", "false"));
  $("report-send").disabled = true;
  state.reportReturnFocus = document.activeElement;
  m.classList.add("active");
  m.querySelector("[data-reason]").focus();
}

function closeReport() {
  $("report-modal").classList.remove("active");
  state.reportReturnFocus?.focus?.();
}

async function sendReport(e) {
  e.preventDefault();
  const m = $("report-modal");
  const reason = m.querySelector('[data-reason][aria-checked="true"]')?.dataset.reason;
  if (!reason) return;
  const details = $("report-details").value.trim();
  $("report-send").disabled = true;
  const ok = await blockPlayer(m.dataset.user, true, details ? `${reason}: ${details}` : reason);
  $("report-send").disabled = false;
  if (ok) closeReport();
}

async function blockPlayer(username, report, reason = null) {
  if (!report && !confirm(`Block ${username}? You'll stop seeing each other in matches, likes and squads in every game. ` +
    `Their public profile page stays visible to people who aren't logged in.`)) {
    return false;
  }
  try {
    await postJson(`${API_BASE}/block`, { to_user: username, game: state.game, report: !!report, reason });
    showToast(report ? "Reported and blocked" : "Blocked", "success");
    removeFromDeck(username);
    lastSquadSignature = null;
    refreshSquad().catch(() => { });
    refreshPending();
    refreshIncoming();
    return true;
  } catch (e) {
    if (!String(e.message).startsWith("AUTH")) showToast(e.message || "Could not block this player", "error");
    return false;
  }
}

/* =========================================================
   INVITES
========================================================= */
async function captureReferral() {
  const ref = localStorage.getItem("pm_ref");
  if (!ref || !state.username) return;
  try {
    await postJson(`${API_BASE}/account/referral`, { ref });
    localStorage.removeItem("pm_ref");
  } catch { }   // keep it and try again next time
}

async function refreshInvite() {
  if (!state.username || inviteLoaded) return;
  try {
    const acc = await apiJson(`${API_BASE}/account`);
    if (acc.avatar !== undefined && acc.avatar !== state.myAvatar) {
      state.myAvatar = acc.avatar;
      paintAvatar($("me-avatar"), state.displayName, state.myAvatar);
      paintAvatar($("me-chip-avatar"), state.displayName, state.myAvatar);
    }
    if (!acc.invite_path) return;
    inviteLoaded = true;
    $("invite-card").style.display = "";
    $("invite-link").value = location.origin + acc.invite_path;
    $("invite-meta").textContent = acc.referrals
      ? `${acc.referrals} friend${acc.referrals === 1 ? "" : "s"} joined with your link 🎉`
      : "No one has joined with your link yet.";
  } catch { }
}

/* =========================================================
   REALTIME
========================================================= */
const BACKGROUND_INTERVAL_MS = 60000;
let baseTitle = document.title;

function canRealtimeRun() {
  return state.hasProfile;
}

// New match while the tab is in the background: flag the tab title + optional system notification
function notifyBackgroundMatch(name) {
  if (document.visibilityState !== "hidden") return;
  baseTitle = document.title.startsWith("🎮") ? baseTitle : document.title;
  document.title = "🎮 New match! — PlayMate";
  if ("Notification" in window && Notification.permission === "granted") {
    try {
      const n = new Notification("It's a match! 🎮", {
        body: `You and ${name} liked each other on PlayMate.`,
        icon: "/static/img/logo.svg",
        tag: "playmate-match",
      });
      n.onclick = () => { window.focus(); n.close(); };
    } catch { }
  }
}

async function realtimeTick() {
  if (!canRealtimeRun()) return;
  // background tab: only look for new squadmates — no ping, so we don't show as online
  const ping = document.visibilityState !== "hidden";
  try { await refreshSocial({ ping }); } catch { }
}

function startRealtime() {
  if (realtimeTimer || !state.hasProfile) return;
  const hidden = document.visibilityState === "hidden";
  if (!hidden) realtimeTick();
  realtimeTimer = setInterval(realtimeTick, hidden ? BACKGROUND_INTERVAL_MS : REALTIME_INTERVAL_MS);
}

function stopRealtime() {
  if (realtimeTimer) clearInterval(realtimeTimer);
  realtimeTimer = null;
}

/* =========================================================
   MOBILE TABS
========================================================= */
function setTab(tab) {
  document.body.dataset.view = tab;
  document.querySelectorAll(".tabbar button").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  if (tab === "squad") $("tab-squad-dot").hidden = true;
  window.scrollTo({ top: 0 });
}

/* =========================================================
   EVENTS
========================================================= */
function setupEventListeners() {
  $("btn-logout").addEventListener("click", clearAuthAndRedirect);
  $("game-chip").addEventListener("click", () => openGamePicker());
  $("game-bar-switch").addEventListener("click", () => openGamePicker());
  $("game-modal-close").addEventListener("click", closeGamePicker);
  els.gameModal.addEventListener("click", (e) => { if (e.target === els.gameModal) closeGamePicker(); });
  $("game-grid").addEventListener("click", (e) => {
    const card = e.target.closest("[data-game]");
    if (card) selectGame(card.dataset.game);
  });

  els.region.addEventListener("change", () => { fillCountries(els.region.value); fillCities(els.region.value, els.country.value); refreshStats(); });
  els.country.addEventListener("change", () => fillCities(els.region.value, els.country.value));
  els.platform.addEventListener("change", updateSteamRow);
  els.btnLooking.addEventListener("click", toggleLooking);

  const runFind = async (e) => {
    e?.preventDefault();
    if (inFlight.find) return;
    if (state.wizard && state.step === 1) return wizardNext();   // Enter on step 1 = Next
    inFlight.find = true;
    const gen = state.gen;
    els.btnFind.disabled = true;
    try {
      if (state.wizard || !state.hasProfile || isDirty()) {
        try { await saveProfile(); } catch { return; }
      }
      if (!isCurrent(gen)) return;
      await findMatches();
    } finally {
      inFlight.find = false;
      // another game was picked meanwhile: its own loading decides when Find is usable again
      if (isCurrent(gen)) els.btnFind.disabled = !state.gameReady;
    }
  };
  els.btnFind.addEventListener("click", runFind);
  els.form.addEventListener("submit", runFind);
  els.btnNext.addEventListener("click", wizardNext);
  els.btnBack.addEventListener("click", () => goToStep(1));
  // any edit of a saved preference updates "Saved ✓ / Unsaved changes" (filters are not preferences)
  const onEdit = (e) => { if (els.step1.contains(e.target) || els.step2.contains(e.target)) renderSaveState(); };
  els.form.addEventListener("input", onEdit);
  els.form.addEventListener("change", onEdit);

  $("btn-refresh-squad").addEventListener("click", async () => {
    const btn = $("btn-refresh-squad");
    btn.classList.add("spinning");
    lastSquadSignature = null;
    try { await refreshSquad(); } catch { } finally { btn.classList.remove("spinning"); }
  });
  $("btn-copy-invite").addEventListener("click", () => copyText($("invite-link").value, "Invite link"));
  $("net-retry").addEventListener("click", () => { hideNetError(); refreshSquad().catch(() => { }); });

  // delegated actions (card buttons, empty states, copy, block, report)
  document.addEventListener("click", (e) => {
    if (!(e.target instanceof Element)) return;
    const t = e.target.closest("[data-action],[data-copy],[data-block-user],[data-report-user],[data-like-back],[data-unmatch-user],[data-reason]");
    if (!t) return;
    if (t.dataset.copy) return copyText(t.dataset.copy, t.dataset.copyLabel || "Text");
    if (t.dataset.blockUser) return blockPlayer(t.dataset.blockUser, false);
    if (t.dataset.reportUser) return openReport(t.dataset.reportUser);
    if (t.dataset.likeBack) return likeBack(t.dataset.likeBack, t);
    if (t.dataset.unmatchUser) return unmatchPlayer(t.dataset.unmatchUser, t.dataset.unmatchKind);
    if (t.dataset.reason) {
      t.closest("[role=radiogroup]").querySelectorAll("[data-reason]").forEach(b => b.setAttribute("aria-checked", String(b === t)));
      $("report-send").disabled = false;
      return;
    }
    switch (t.dataset.action) {
      case "skip": return handleSkip();
      case "like": return handleLike();
      case "find": return runFind();
      case "switch": return openGamePicker();
      case "edit-profile": return setTab("profile");
      case "retry-load": {
        const g = state.game;
        state.game = null;
        return selectGame(g).then(() => { els.btnFind.disabled = !state.gameReady; });
      }
      case "looking": return toggleLooking();
      case "more": return findMatches();
      case "reset-skipped":
        clearSkipped();
        return findMatches();
      case "clear-filters":
        els.optSameLang.checked = false;
        els.optLookingOnly.checked = false;
        return findMatches();
      case "invite":
        if ($("invite-link").value) copyText($("invite-link").value, "Invite link");
        else showToast("Save your profile to get your invite link", "info");
        return;
    }
  });

  // keyboard: ← skip, → like, Esc closes dialogs
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && $("report-modal").classList.contains("active")) return closeReport();
    if (e.target instanceof Element && e.target.closest("input, select, textarea")) return;
    if (e.key === "Escape") {
      if ($("report-modal").classList.contains("active")) return closeReport();
      if (els.modal.classList.contains("active")) return closeModal();
      if (els.gameModal.classList.contains("active")) return closeGamePicker();
    }
    if (els.modal.classList.contains("active") || els.gameModal.classList.contains("active") ||
        $("report-modal").classList.contains("active") || !$("active-card")) return;
    if (e.key === "ArrowLeft") handleSkip();
    if (e.key === "ArrowRight") handleLike();
  });

  document.querySelectorAll(".tabbar button").forEach(b => b.addEventListener("click", () => setTab(b.dataset.tab)));
  $("report-form").addEventListener("submit", sendReport);
  $("modal-close-btn").addEventListener("click", closeModal);
  $("btn-keep-matching").addEventListener("click", closeModal);
  $("btn-view-squad").addEventListener("click", goToSquad);
  $("report-cancel").addEventListener("click", closeReport);
  $("report-modal").addEventListener("click", (e) => { if (e.target === $("report-modal")) closeReport(); });

  document.addEventListener("visibilitychange", () => {
    // slower polling in the background, normal speed when visible
    stopRealtime();
    startRealtime();
    if (document.visibilityState === "visible" && document.title.startsWith("🎮")) document.title = baseTitle;
  });
  window.addEventListener("pagehide", stopRealtime);
  window.addEventListener("beforeunload", (e) => {
    if (leaving || !isDirty()) return;
    e.preventDefault();
    e.returnValue = "";   // the browser shows its own "leave site?" prompt
  });
}

// broken cover image -> our own SVG art (data-fallback); no inline onerror, so the CSP needs no 'unsafe-inline'
document.addEventListener("error", (e) => {
  const img = e.target;
  if (img instanceof HTMLImageElement && img.dataset.fallback && !img.src.endsWith(img.dataset.fallback)) {
    img.src = img.dataset.fallback;
    delete img.dataset.fallback;
  }
}, true);

/* =========================================================
   INIT
========================================================= */
document.addEventListener("DOMContentLoaded", async () => {
  await syncTokenFromSession();
  if (!getAccessToken()) {
    // not logged in: remember which game they wanted, so they land on it after signing up
    const q = new URLSearchParams(location.search);
    const wanted = q.get("game"), next = q.get("next") || "";
    const keep = new URLSearchParams();
    if (wanted && /^[a-z0-9-]{2,20}$/.test(wanted)) keep.set("game", wanted);
    if (/^\/u\/[A-Za-z0-9_.-]{3,24}$/.test(next)) keep.set("next", next);
    window.location.href = keep.toString() ? `/?${keep}` : "/";
    return;
  }
  localStorage.removeItem("pm_last_squad_sig"); // old versions
  ensureCacheOwner();
  pageUid = tokenUserId();
  setupEventListeners();

  const cachedName = (localStorage.getItem("pm_username") || "").trim();
  if (cachedName) {
    $("me-chip-name").textContent = cachedName;
    paintAvatar($("me-chip-avatar"), cachedName);
  }

  try {
    await Promise.all([loadGames(), loadMyGames()]);
  } catch {
    showNetError();
    return;
  }

  captureIntentFromUrl();
  const fromUrl = new URLSearchParams(location.search).get("game");
  const saved = localStorage.getItem("pm_game");
  const pick = [fromUrl, saved, state.myGames[0]].find(g => g && state.games.some(x => x.id === g));

  if (pick) {
    await selectGame(pick);
    if (new URLSearchParams(location.search).has("pick")) openGamePicker();
    if (new URLSearchParams(location.search).get("tab") === "squad") {   // e.g. "In your squad — open it" on a profile
      setTab("squad");
      $("squad-panel")?.scrollIntoView({ block: "start" });
    }
  } else {
    // brand-new user: choose a first game
    state.game = null;
    els.cardWrapper.innerHTML = `<div class="empty-state"><h3>Welcome to PlayMate 👋</h3><p>Pick the game you want to find teammates for.</p>
      <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="switch">Choose a game</button></div></div>`;
    openGamePicker(true);
  }

  await captureReferral();
  refreshInvite();
});
