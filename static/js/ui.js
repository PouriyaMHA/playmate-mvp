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

// supabase-js refreshes the session in the background; keep our copy of the token in sync
supabaseClient?.auth.onAuthStateChange((_event, session) => {
  if (session?.access_token) localStorage.setItem("pm_access_token", session.access_token);
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

function clearAuthAndRedirect() {
  ["pm_access_token", "pm_username", "pm_username_locked", "playmate_profile"].forEach(k => localStorage.removeItem(k));
  // Supabase session keys, so the landing page doesn't log straight back in
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const k = localStorage.key(i);
    if (k && k.startsWith("sb-") && k.endsWith("-auth-token")) localStorage.removeItem(k);
  }
  stopRealtime();
  window.location.href = "/";
}

async function authFetch(url, options = {}) {
  const token = getAccessToken();
  if (!token) {
    clearAuthAndRedirect();
    throw new Error("AUTH_MISSING");
  }
  const send = (t) => fetch(url, { ...options, headers: { ...(options.headers || {}), Authorization: `Bearer ${t}` } });
  let res = await send(token);
  if (res.status === 401) {
    // token probably expired: refresh once and retry before logging out
    const fresh = await refreshAccessToken();
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
};

const inFlight = { match: false, like: false, ping: false, pending: false, squadPromise: null, squadGame: null };
const announced = new Set();   // squadmates we already showed a match modal for (per game: "game:user")
let inviteLoaded = false;
let realtimeTimer = null;
let lastSquadSignature = "";
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
  usernameRow: $("username-row"),
  usernameInput: $("username-input"),
  btnLooking: $("btn-looking"),
  btnFind: $("btn-find-matches"),
  optSameLang: $("opt-same-language"),
  optLookingOnly: $("opt-looking-only"),
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
        <img src="${esc(g.cover)}" alt="" loading="lazy" onerror="this.onerror=null;this.src='${esc(g.art || "/static/img/games/default.svg")}'">
        ${g.players >= SHOW_COUNTS_FROM ? `<span class="game-card-body"><span class="game-card-meta">${g.players} players</span></span>` : ""}
        ${mine ? `<span class="game-card-tag">${current ? "Playing" : "Added"}</span>` : ""}
      </button>`;
  }).join("");
}

function openGamePicker(firstTime = false) {
  renderGamePicker();
  $("game-modal-title").textContent = firstTime ? "Pick your first game" : "Choose your game";
  $("game-modal-close").style.display = firstTime && !state.game ? "none" : "";
  els.gameModal.classList.add("active");
}

function closeGamePicker() {
  if (!state.game) return; // must pick one first
  els.gameModal.classList.remove("active");
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
  try {
    const region = state.profile.region || els.region.value || "";
    const res = await fetch(`${API_BASE}/stats?game=${encodeURIComponent(state.game)}&region=${encodeURIComponent(region)}`);
    const s = await res.json();
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
  els.gameModal.classList.remove("active");
  if (sameGame) return;

  stopRealtime();
  state.game = gameId;
  localStorage.setItem("pm_game", gameId);
  const url = new URL(location.href);
  url.searchParams.set("game", gameId);
  history.replaceState(null, "", url);

  // reset per-game state
  state.matches = [];
  state.currentMatchIndex = 0;
  state.squad = [];
  lastSquadSignature = "";
  lastSquadUsernames = new Set();
  squadBootstrapped = false;
  inFlight.squadPromise = null;
  state.loadFailed = false;
  renderSquadList();
  renderPendingList([]);

  try {
    const res = await fetch(`${API_BASE}/meta/${encodeURIComponent(gameId)}`);
    if (!res.ok) throw new Error("meta");
    state.meta = await res.json();
  } catch {
    showToast("Could not load this game", "error");
    return;
  }

  buildForm();
  await loadProfileForGame();
  renderGameChrome();
  refreshStats();
  renderIdleCenter();

  if (state.hasProfile) {
    startRealtime();
    refreshSquad().catch(() => { });
    refreshPending();
    // returning player: show matches straight away instead of making them press Find Matches
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
  $("ign-label").textContent = m.ign_label || "In-game name";
  els.ign.placeholder = `Your ${m.ign_label || "in-game name"}`;

  els.gameFields.innerHTML = m.fields.map(f => `
    <div class="field-row">
      <label class="field-label" for="gf-${esc(f.id)}">${svgIcon(FIELD_ICONS[f.id] || "class")}${esc(f.label)}</label>
      <select id="gf-${esc(f.id)}" data-field="${esc(f.id)}" ${f.required ? "required" : ""}>
        <option value="">${f.required ? "Select…" : "Optional — skip or select…"}</option>
        ${f.options.map(o => `<option value="${esc(o)}">${esc(o)}</option>`).join("")}
      </select>
    </div>`).join("");

  els.langContainer.innerHTML = "";
  m.languages.forEach(l => {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "lang-pill";
    pill.dataset.code = l.code;
    pill.textContent = l.label;
    pill.addEventListener("click", () => pill.classList.toggle("active"));
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
  els.langContainer.querySelectorAll(".lang-pill").forEach(pill => pill.classList.toggle("active", langs.has(pill.dataset.code)));
  els.ign.value = p.in_game_username || "";
  els.discord.value = p.discord_username || "";
  const fields = p.fields || {};
  els.gameFields.querySelectorAll("select[data-field]").forEach(s => { s.value = fields[s.dataset.field] || ""; });
}

async function loadProfileForGame() {
  state.hasProfile = false;
  state.profile = {};
  try {
    const p = await apiJson(`${API_BASE}/my-profile?game=${encodeURIComponent(state.game)}`);
    state.profile = p;
    if (p.avatar) state.myAvatar = p.avatar;
    state.hasProfile = true;
    setIdentity(p.display_username || p.username);
    applyProfileToForm(p);
    els.status.textContent = "";
  } catch (e) {
    if (e.status !== 404) {
      state.loadFailed = true;
      els.btnFind.disabled = true;
      els.cardWrapper.innerHTML = `<div class="empty-state"><h3>Couldn't load your profile</h3>
        <p>Check your connection and try again.</p>
        <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="retry-load">Try again</button></div></div>`;
      return;
    }
    // new game: prefill what is shared between games (from another game profile, else the local cache)
    let shared = JSON.parse(localStorage.getItem("playmate_shared") || "{}");
    const other = state.myGames.find(g => g !== state.game);
    if (other) {
      try {
        const o = await apiJson(`${API_BASE}/my-profile?game=${encodeURIComponent(other)}`);
        shared = { region: o.region, country: o.country, city: o.city, mic: o.mic, languages: o.languages, discord_username: o.discord_username };
        setIdentity(o.display_username || o.username);
      } catch { }
    }
    applyProfileToForm({ ...shared, in_game_username: "", fields: {} });
    els.status.textContent = `New ${gameInfo(state.game)?.name || ""} profile — fill in the game details and hit Find Matches.`;
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

function collectProfile() {
  const fields = {};
  els.gameFields.querySelectorAll("select[data-field]").forEach(s => { if (s.value) fields[s.dataset.field] = s.value; });
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
document.addEventListener("change", (e) => e.target.classList?.remove("field-invalid"));
document.addEventListener("input", (e) => e.target.classList?.remove("field-invalid"));
document.addEventListener("click", (e) => {
  if (e.target.closest?.(".lang-pill")) els.langContainer.classList.remove("field-invalid");
});

async function saveProfile() {
  if (state.loadFailed) {
    showToast("Your profile didn't load — tap Try again first", "error");
    throw new Error("Validation");
  }
  const payload = collectProfile();
  const missing = validateProfile(payload);
  if (missing.length) {
    markMissing(missing);
    showToast(`Please fill in: ${missing.map(m => m.label).join(", ")}`, "error");
    throw new Error("Validation");
  }
  try {
    const d = await postJson(`${API_BASE}/profile`, payload);
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
      region: payload.region, country: payload.country, city: payload.city, mic: payload.mic, languages: payload.languages,
      discord_username: payload.discord_username,
    }));
    els.status.textContent = "";
    renderGameChrome();
    renderLookingButton();
    startRealtime();
    await captureReferral();
    refreshInvite();
  } catch (e) {
    if (e.message !== "AUTH_EXPIRED" && e.message !== "AUTH_MISSING") showToast(e.message || "Failed to save profile", "error");
    throw e;
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
        <img class="empty-cover" src="${esc(g?.cover || "")}" alt="" onerror="this.onerror=null;this.src='${esc(g?.art || "/static/img/games/default.svg")}'">
        <h3>Ready when you are</h3>
        <p>Hit <b>Find Matches</b> to see ${esc(g?.name || "")} players who fit how you play.</p>
        <div style="margin-top:16px;"><button class="btn-primary" type="button" data-action="find">Find Matches</button></div>
      </div>`
    : `<div class="empty-state">
        <img class="empty-cover" src="${esc(g?.cover || "")}" alt="" onerror="this.onerror=null;this.src='${esc(g?.art || "/static/img/games/default.svg")}'">
        <h3>Set up your ${esc(g?.name || "")} profile</h3>
        <p>Fill in the form — region, game details and languages — then hit <b>Find Matches</b>.</p>
        <div class="mobile-only" style="margin-top:16px;"><button class="btn-primary" type="button" data-action="edit-profile">Set up profile</button></div>
      </div>`;
}

function renderNoMatches(total) {
  const s = state.stats || {};
  const filtered = els.optSameLang.checked || els.optLookingOnly.checked;
  els.cardWrapper.innerHTML = `
    <div class="empty-state wide">
      <h3>${total === 0 ? "No new players right now" : "You're all caught up"}</h3>
      <p>${filtered
      ? "Your filters are hiding some players. Turn them off to see everyone."
      : `PlayMate is in early access — every new ${esc(gameInfo(state.game)?.name || "")} player makes your matches better. Help it grow:`}</p>
      <div class="empty-actions">
        ${filtered ? `<button class="btn-primary" type="button" data-action="clear-filters">Show everyone</button>` : ""}
        <button class="empty-action" type="button" data-action="looking">${svgIcon("bolt")}<span><b>Turn on "Looking now"</b><br>Show up first for 1 hour</span></button>
        <button class="empty-action" type="button" data-action="invite">${svgIcon("link")}<span><b>Invite friends</b><br>Copy your invite link</span></button>
        <button class="empty-action" type="button" data-action="switch">${svgIcon("gamepad")}<span><b>Add another game</b><br>More games, more squads</span></button>
      </div>
      <div style="margin-top:16px;"><button class="btn-secondary" type="button" data-action="find">Scan again</button></div>
    </div>`;
}

async function findMatches({ keepTab = false } = {}) {
  if (state.loading || inFlight.match || !state.game) return;
  inFlight.match = true;
  const game = state.game;
  if (!keepTab && window.innerWidth <= 760) setTab("match");   // results (and errors) are shown on the Match tab
  try {
    setLoading(true);
    const data = await postJson(`${API_BASE}/match`, {
      game,
      same_language_only: els.optSameLang.checked,
      looking_only: els.optLookingOnly.checked,
    });
    if (state.game !== game) { setLoading(false); return; }   // switched game while loading
    state.matches = data.matches || [];
    state.currentMatchIndex = 0;
    setLoading(false);
    await refreshStats();
    if (!state.matches.length) return renderNoMatches(data.total);
    renderCard();
  } catch (e) {
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
    // the player switched game mid-scan: load the new game's matches instead
    if (state.game !== game && state.hasProfile) findMatches({ keepTab: true });
  }
}

function renderCard() {
  if (state.loading) return;
  if (state.currentMatchIndex >= state.matches.length) return renderNoMatches(state.matches.length);

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
    ${match.looking_now ? '<div style="margin-top:8px;"><span class="looking-badge">● Looking for a squad now</span></div>' : ""}

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
    <button class="action-btn btn-like" type="button" data-action="like" aria-label="Add to squad" title="Add to squad (→)">${svgIcon("heart")}</button>
    Add to squad
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
  if (state.loading || inFlight.like) return;
  const card = $("active-card");
  if (!card) return;
  card.classList.add("swipe-left");
  setTimeout(() => {
    state.currentMatchIndex++;
    renderCard();
  }, 280);
}

/* =========================================================
   LIKES
========================================================= */
async function handleLike() {
  if (state.loading || inFlight.like) return;
  const matchUser = state.matches[state.currentMatchIndex];
  if (!matchUser) return;
  inFlight.like = true;

  const card = $("active-card");
  const buttons = document.querySelectorAll(".action-btn");
  buttons.forEach(b => b.disabled = true);
  if (card) card.classList.add("swipe-right");
  let liked = true;

  try {
    const data = await postJson(`${API_BASE}/like`, { to_user: matchUser.username, game: state.game });
    const isMutual = data?.mutual === true || data?.status === "mutual";
    const mp = matchUser.profile || {};
    const mate = { username: matchUser.username, display_username: mp.display_username || matchUser.username, in_game_username: null };

    if (isMutual) {
      // the in-game name is only revealed by the squad endpoint
      const key = (matchUser.username || "").toLowerCase();
      announced.add(`${state.game}:${key}`);
      try { await inFlight.squadPromise; } catch { }
      try { await refreshSquad({ silent: true }); } catch { }
      const fromSquad = (state.squad || []).find(m => (m.username || "").toLowerCase() === key);
      if (fromSquad?.in_game_username) mate.in_game_username = fromSquad.in_game_username;
      triggerMatchModal(mate, { kind: "match" });
    } else {
      triggerMatchModal(mate, { kind: "like" });
      refreshSquad().catch(() => { });
    }
    refreshPending();
  } catch (e) {
    liked = false;
    if (!String(e.message).startsWith("AUTH")) showToast(e.message || "Could not send like", "error");
  } finally {
    setTimeout(() => {
      if (liked) {
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
    .map(m => `${(m.username || "").toLowerCase()}|${m.in_game_username || ""}|${m.discord_username || ""}|${m.looking_now ? 1 : 0}|${m.last_active || ""}`)
    .sort()
    .join(";");
}

async function refreshSquad(opts = {}) {
  if (!state.game || !state.hasProfile) return;
  if (inFlight.squadPromise && inFlight.squadGame === state.game) return inFlight.squadPromise;
  const game = state.game;
  inFlight.squadGame = game;

  inFlight.squadPromise = (async () => {
    const res = await authFetch(`${API_BASE}/my-squad-details?game=${encodeURIComponent(game)}`);
    if (game !== state.game) return;            // user switched game meanwhile
    if (res.status === 404) {
      state.squad = [];
      squadBootstrapped = true;
      return renderSquadList();
    }
    if (!res.ok) throw new Error(`squad failed: ${res.status}`);
    const newSquad = (await res.json()).squadmates || [];

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
          in_game_username: mate.in_game_username,
        });
        notifyBackgroundMatch(mate.display_username || mate.username);
        if (window.innerWidth <= 760) $("tab-squad-dot").hidden = false;
      }
    }
  })();

  try {
    return await inFlight.squadPromise;
  } catch (err) {
    console.error("Squad fetch error", err);
    if (!String(err.message).startsWith("AUTH")) showNetError();
    throw err;
  } finally {
    if (inFlight.squadGame === game) inFlight.squadPromise = null;
  }
}

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
    const name = mate.display_username || mate.username || "";
    return `
      <div class="squad-member">
        <span class="status-dot ${status}"></span>
        <a class="sm-avatar avatar-face${avatarClass(mate.avatar)}" href="/u/${encodeURIComponent(mate.username)}" target="_blank" rel="noopener" style="--hue:${avatarHue(name)}">${avatarInner(name, mate.avatar)}</a>
        <div class="sm-info">
          <a class="sm-name" href="/u/${encodeURIComponent(mate.username)}" target="_blank" rel="noopener">${esc(name)}</a>
          <span class="sm-status ${status}">${esc(statusText)}</span>
          <span class="sm-ign">${esc(state.meta?.ign_label || "In-game")}: <b>${esc(ign || "—")}</b>${discord ? `<br>Discord: <b>${esc(discord)}</b>` : ""}</span>
          <div class="sm-actions">
            ${ign ? `<button type="button" class="sm-btn" data-copy="${esc(ign)}" data-copy-label="${esc(state.meta?.ign_label || "In-game name")}">Copy ${esc(state.meta?.ign_label || "name")}</button>` : ""}
            ${discord ? `<button type="button" class="sm-btn" data-copy="${esc(discord)}" data-copy-label="Discord">Copy Discord</button>` : ""}
            <button type="button" class="sm-btn danger" data-block-user="${esc(mate.username)}">Block</button>
          </div>
        </div>
      </div>`;
  }).join("");
}

async function refreshPending() {
  if (!state.game || !state.hasProfile || inFlight.pending) return;
  inFlight.pending = true;
  const game = state.game;
  try {
    const res = await authFetch(`${API_BASE}/pending-likes?game=${encodeURIComponent(game)}`);
    if (!res.ok || game !== state.game) return;
    renderPendingList((await res.json()).pending || []);
  } catch (e) {
    console.warn("Pending likes fetch failed", e);
  } finally {
    inFlight.pending = false;
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

  els.modal.classList.toggle("is-like", kind === "like");
  els.modal.classList.add("active");
}

function closeModal() {
  els.modal.classList.remove("active");
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
  try {
    const d = await postJson(`${API_BASE}/looking`, { minutes: turningOn ? 60 : 0, game: state.game });
    state.profile.looking_until = d.looking_until;
    renderLookingButton();
    refreshStats();
    showToast(turningOn ? "You're shown as looking for 1 hour" : "Stopped looking", "success");
  } catch (e) {
    if (!String(e.message).startsWith("AUTH")) showToast(e.message || "Could not update your status", "error");
  }
}

async function blockPlayer(username, report) {
  let reason = null;
  if (report) {
    reason = prompt(`Report ${username}: what happened? (they will also be blocked)`);
    if (reason === null) return;
  } else if (!confirm(`Block ${username}? You won't see each other anymore.`)) {
    return;
  }
  try {
    await postJson(`${API_BASE}/block`, { to_user: username, game: state.game, report: !!report, reason });
    showToast(report ? "Reported and blocked" : "Blocked", "success");
    const key = String(username).toLowerCase();
    const before = state.matches.length;
    state.matches = state.matches.filter((m, i) => {
      const drop = (m.username || "").toLowerCase() === key;
      if (drop && i < state.currentMatchIndex) state.currentMatchIndex--;
      return !drop;
    });
    if (state.matches.length !== before) renderCard();
    lastSquadSignature = "";
    refreshSquad().catch(() => { });
    refreshPending();
  } catch (e) {
    if (!String(e.message).startsWith("AUTH")) showToast(e.message || "Could not block this player", "error");
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
  } catch { }
  localStorage.removeItem("pm_ref");
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
  if (document.visibilityState === "hidden") {
    // background: only look for new squadmates (no ping, so we don't show as online)
    try { await refreshSquad({ silent: true }); } catch { }
    return;
  }
  if (!inFlight.ping) {
    inFlight.ping = true;
    try {
      const res = await authFetch(`${API_BASE}/ping?game=${encodeURIComponent(state.game)}`, { method: "POST" });
      if (res.ok) hideNetError();
    } catch (e) {
      if (!String(e.message).startsWith("AUTH")) showNetError();
    } finally {
      inFlight.ping = false;
    }
  }
  try {
    await refreshSquad({ silent: true });
    hideNetError();
  } catch { }
  refreshPending();
  renderLookingButton();
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
  els.btnLooking.addEventListener("click", toggleLooking);

  const runFind = async (e) => {
    e?.preventDefault();
    try { await saveProfile(); } catch { return; }
    await findMatches();
  };
  els.btnFind.addEventListener("click", runFind);
  els.form.addEventListener("submit", runFind);

  $("btn-refresh-squad").addEventListener("click", async () => {
    const btn = $("btn-refresh-squad");
    btn.classList.add("spinning");
    lastSquadSignature = "";
    try { await refreshSquad(); await refreshPending(); } catch { } finally { btn.classList.remove("spinning"); }
  });
  $("btn-copy-invite").addEventListener("click", () => copyText($("invite-link").value, "Invite link"));
  $("net-retry").addEventListener("click", () => { hideNetError(); refreshSquad().catch(() => { }); });

  // delegated actions (card buttons, empty states, copy, block, report)
  document.addEventListener("click", (e) => {
    if (!(e.target instanceof Element)) return;
    const t = e.target.closest("[data-action],[data-copy],[data-block-user],[data-report-user]");
    if (!t) return;
    if (t.dataset.copy) return copyText(t.dataset.copy, t.dataset.copyLabel || "Text");
    if (t.dataset.blockUser) return blockPlayer(t.dataset.blockUser, false);
    if (t.dataset.reportUser) return blockPlayer(t.dataset.reportUser, true);
    switch (t.dataset.action) {
      case "skip": return handleSkip();
      case "like": return handleLike();
      case "find": return runFind();
      case "switch": return openGamePicker();
      case "edit-profile": return setTab("profile");
      case "retry-load": {
        const g = state.game;
        state.game = null;
        return selectGame(g).then(() => { els.btnFind.disabled = false; });
      }
      case "looking": return toggleLooking();
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
    if (e.target instanceof Element && e.target.closest("input, select, textarea")) return;
    if (e.key === "Escape") {
      if (els.modal.classList.contains("active")) return closeModal();
      if (els.gameModal.classList.contains("active")) return closeGamePicker();
    }
    if (els.modal.classList.contains("active") || els.gameModal.classList.contains("active") || !$("active-card")) return;
    if (e.key === "ArrowLeft") handleSkip();
    if (e.key === "ArrowRight") handleLike();
  });

  document.querySelectorAll(".tabbar button").forEach(b => b.addEventListener("click", () => setTab(b.dataset.tab)));

  document.addEventListener("visibilitychange", () => {
    // slower polling in the background, normal speed when visible
    stopRealtime();
    startRealtime();
    if (document.visibilityState === "visible" && document.title.startsWith("🎮")) document.title = baseTitle;
  });
  window.addEventListener("beforeunload", stopRealtime);
}

/* =========================================================
   INIT
========================================================= */
document.addEventListener("DOMContentLoaded", async () => {
  await syncTokenFromSession();
  if (!getAccessToken()) {
    window.location.href = "/";
    return;
  }
  localStorage.removeItem("pm_last_squad_sig"); // old versions
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

  const fromUrl = new URLSearchParams(location.search).get("game");
  const saved = localStorage.getItem("pm_game");
  const pick = [fromUrl, saved, state.myGames[0]].find(g => g && state.games.some(x => x.id === g));

  if (pick) {
    await selectGame(pick);
    if (new URLSearchParams(location.search).has("pick")) openGamePicker();
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
