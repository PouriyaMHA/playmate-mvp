/* =========================================================
   PlayMate BF — ui.html script (refactored for readability)
   Logic unchanged; formatting + organization only.
   ========================================================= */

/* -----------------------
   GLOBALS / CONSTANTS
------------------------*/
const REALTIME_INTERVAL_MS = 15000; // 15s


// In-memory only: a persisted signature made the squad never render after a reload
// (the "no modal on first load" case is handled by squadBootstrapped)
let lastSquadSignature = "";
localStorage.removeItem("pm_last_squad_sig"); // clean up old versions


const API_BASE = '/api'; // Relative path as requested

const GAME = "battlefield";
let META = null;

// --- AUTH HELPERS (Step 10A) ---

function clearAuthAndRedirect() {
  localStorage.removeItem("pm_access_token");
  localStorage.removeItem("pm_username");
  // Don't leave this user's profile for the next person on this browser
  localStorage.removeItem("pm_username_locked");
  localStorage.removeItem("playmate_profile");

  // Clear Supabase auth session keys so Landing won't auto-redirect
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const k = localStorage.key(i);
    if (k && k.startsWith("sb-") && k.endsWith("-auth-token")) {
      localStorage.removeItem(k);
    }
  }

  stopRealtime();
  window.location.href = "/";
}


// Same public (anon) key as landing.html
const SUPABASE_URL = "https://fffejwdrqhizgxpjacgn.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmZmVqd2RycWhpemd4cGphY2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTExNjgsImV4cCI6MjA4MDc4NzE2OH0.Zr2And6oP8PKmCDiW3rNcimBWh5cUV22YvnWwhQQz7s";
const supabaseClient = window.supabase?.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) || null;

// supabase-js refreshes the session in the background; keep our copy of the token in sync
supabaseClient?.auth.onAuthStateChange((_event, session) => {
  if (session?.access_token) localStorage.setItem("pm_access_token", session.access_token);
});

// Get a fresh access token from the Supabase session (null if there is no session)
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
    const token = data?.session?.access_token;
    if (token) localStorage.setItem("pm_access_token", token);
  } catch { }
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
    // Token probably expired: refresh once and retry before logging out
    const fresh = await refreshAccessToken();
    if (fresh) res = await send(fresh);
  }

  if (res.status === 401) {
    // Auth problem, not "connection issue"
    clearAuthAndRedirect();
    throw new Error("AUTH_EXPIRED");
  }

  return res;
}


function getAccessToken() {
  return localStorage.getItem("pm_access_token") || "";
}

function withAuthHeaders(headers = {}) {
  const t = getAccessToken();
  // اگر توکن نبود، همون headers را برگردان (بعداً می‌تونیم redirect کنیم)
  if (!t) return { ...headers };
  return { ...headers, Authorization: `Bearer ${t}` };
}

function authHeaders(headers = {}) {
  return withAuthHeaders(headers);
}


/* Realtime (single timer) */
let realtimeTimer = null;

/* In-flight guards (Step 9E) */
const inFlight = {
  match: false,
  like: false,
  squad: false,
  ping: false,
  pending: false,

  // NEW: share the same in-flight promise so callers don't "return" and miss updates
  squadPromise: null
};


/* -----------------------
   STATE
------------------------*/
const state = {
  profile: {
    username: "",
    display_username: "",
    region: "",
    city: "",
    platform: "PC",
    in_game_username: "",
    favorite_mode: "Conquest",
    class_type: "Assault",
    mic: "voice",
    languages: []
  },
  matches: [],
  currentMatchIndex: 0,
  squad: [],
  loading: false
};

/* -----------------------
   DOM ELEMENTS
------------------------*/
const els = {
  form: document.getElementById("profile-form"),
  status: document.getElementById("profile-status"),
  langContainer: document.getElementById("lang-container"),
  cardWrapper: document.getElementById("card-wrapper"),
  squadList: document.getElementById("squad-list"),
  pendingSection: document.getElementById("pending-section"),
  pendingList: document.getElementById("pending-list"),
  pendingCount: document.getElementById("pending-count"),
  modal: document.getElementById("match-modal"),
  viewProfileLink: document.getElementById("view-profile-link"),

  region: document.getElementById("region"),
  city: document.getElementById("city"),
  favoriteMode: document.getElementById("favorite_mode"),
  platform: document.getElementById("platform"),
  classType: document.getElementById("class_type"),
  mic: document.getElementById("mic"),
  ign: document.getElementById("in_game_username"),
  discord: document.getElementById("discord_username"),
  btnLooking: document.getElementById("btn-looking"),
  usernameHidden: document.getElementById("username"),
  pmUsernameDisplay: document.getElementById("pm-username-display"),


  btnFind: document.getElementById("btn-find-matches"),
  btnLogout: document.getElementById("btn-logout")

};

/* =========================================================
   INIT
========================================================= */
document.addEventListener("DOMContentLoaded", async () => {

  // Pick up a fresh token if the Supabase session was refreshed while away
  await syncTokenFromSession();

  // HARD GATE: no token => go landing (avoid 401 spam)
  const t = getAccessToken();
  if (!t) {
    window.location.href = "/";
    return;
  }

  // Logout should always work (do not depend on meta/region)
  if (els.btnLogout) {
    els.btnLogout.addEventListener("click", clearAuthAndRedirect);
  }

  try {
    await loadMeta();
    populateRegions();
    populateFavoriteModes();
    renderLanguagesFromMeta();
  } catch (e) {
    console.error(e);
    showToast("Failed to load game meta", "error");
  }

  // Now that select options + language pills exist, restore works.
  // Show the cached copy instantly, then replace it with the server copy.
  loadProfileFromStorage();
  await loadProfileFromServer();
  initLockedUsernameFromStorage();

  if ((state.profile.username || "").trim()) startRealtime();

  setupEventListeners();

  // Restore language pills after pills created from meta
  applyStoredLanguagesToPills();

  // If region from storage set, rebuild city list
  if (state.profile.region) {
    els.region.value = normalizeRegionId(state.profile.region);
    els.region.dispatchEvent(new Event("change"));
    if (state.profile.city) els.city.value = state.profile.city;
  }


  if (state.profile.username) {
    refreshSquad();
    refreshPending();
  }

});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    stopRealtime();
  } else {
    if ((state.profile.username || "").trim()) startRealtime();
  }
});

window.addEventListener("beforeunload", () => stopRealtime());

/* =========================================================
   HELPERS
========================================================= */
const netBanner = document.getElementById("net-banner");
const netRetryBtn = document.getElementById("net-retry");

function showNetError() {
  if (netBanner) netBanner.style.display = "flex";
}

function hideNetError() {
  if (netBanner) netBanner.style.display = "none";
}

netRetryBtn?.addEventListener("click", () => {
  hideNetError();
  findMatches();
  refreshSquad();
});

function setLockedUsername(displayUsername) {
  const d = (displayUsername || "").trim();
  if (!d) return;

  state.profile.display_username = d;
  state.profile.username = d.toLowerCase();

  // persist (source of truth for UI)
  localStorage.setItem("pm_username", d);
  localStorage.setItem("pm_username_locked", "1");

  if (els.pmUsernameDisplay) els.pmUsernameDisplay.textContent = d;
  paintAvatar(document.getElementById("me-avatar"), d);
  if (els.usernameHidden) els.usernameHidden.value = d;

  updateProfileLink(state.profile.username);
}

function initLockedUsernameFromStorage() {
  // priority: pm_username set at Landing, otherwise keep what loadProfileFromStorage set
  const fromLanding = (localStorage.getItem("pm_username") || "").trim();
  if (fromLanding && !state.profile.display_username) {
    setLockedUsername(fromLanding);
  } else if (state.profile.display_username) {
    setLockedUsername(state.profile.display_username);
  }
}


function normalizeRegionId(rawRegion) {
  const raw = (rawRegion || "").trim();
  if (!raw) return "";

  const regions = META?.regions || [];

  // اگر از قبل id بود (na-west)
  let r = regions.find(x => x.id === raw);
  if (r) return r.id;

  // اگر label ذخیره شده بود (North America West)
  r = regions.find(x => (x.label || "").trim().toLowerCase() === raw.toLowerCase());
  if (r) return r.id;

  return "";
}


function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  document.getElementById("toast-container").appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

function initialOf(name) {
  return name ? String(name).trim().substring(0, 1).toUpperCase() || "?" : "?";
}

// HTML-safe initial (for innerHTML templates)
function getInitials(name) {
  return esc(initialOf(name));
}

// Stable colour per player, so avatars are told apart at a glance
function avatarHue(name) {
  let h = 0;
  for (const ch of String(name || "").toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

function paintAvatar(el, name) {
  if (!el) return;
  el.textContent = initialOf(name);
  el.style.setProperty("--hue", avatarHue(name));
}

function svgIcon(id) {
  return `<svg class="icon"><use href="#i-${id}"/></svg>`;
}

const MIC_LABELS = { voice: "Voice", both: "Voice + Text", none: "No mic" };

function langLabels(codes) {
  const map = Object.fromEntries((META?.languages || []).map(l => [l.code, l.label]));
  return String(codes || "").split(",").map(c => c.trim()).filter(Boolean).map(c => map[c] || c).join(", ");
}

// online (<=60s), away (<=10min), offline
function presenceOf(lastActiveIso) {
  const t = lastActiveIso ? new Date(lastActiveIso).getTime() : NaN;
  if (!Number.isFinite(t)) return "offline";
  const sec = (Date.now() - t) / 1000;
  if (sec <= 60) return "online";
  if (sec <= 600) return "away";
  return "offline";
}

// Escape anything user-provided before it goes into innerHTML (prevents XSS)
function esc(value) {
  return String(value ?? "").replace(/[&<>"'`]/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;"
  })[ch]);
}

function regionLabel(id) {
  const r = (META?.regions || []).find(x => x.id === id);
  return r ? r.label : (id || "");
}

async function copyText(text, label) {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`${label} copied`, "success");
  } catch {
    showToast(`${label}: ${text}`, "info");
  }
}

// ---- Looking for a squad now ----
function renderLookingButton() {
  const btn = els.btnLooking;
  if (!btn) return;
  const until = state.profile.looking_until ? new Date(state.profile.looking_until).getTime() : 0;
  const on = until > Date.now();
  btn.style.display = state.profile.username ? "" : "none";
  btn.classList.toggle("on", on);
  if (on) {
    const mins = Math.max(1, Math.round((until - Date.now()) / 60000));
    btn.textContent = `🟢 Looking for a squad · ${mins} min left (tap to stop)`;
  } else {
    btn.textContent = "🟢 I'm looking for a squad now";
  }
}

async function toggleLooking() {
  const until = state.profile.looking_until ? new Date(state.profile.looking_until).getTime() : 0;
  const turningOn = !(until > Date.now());
  try {
    const res = await authFetch(`${API_BASE}/looking`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ minutes: turningOn ? 60 : 0, game: GAME })
    });
    if (res.status === 404) {
      showToast("Save your profile first", "error");
      return;
    }
    if (!res.ok) throw new Error(`looking failed: ${res.status}`);
    const data = await res.json();
    state.profile.looking_until = data.looking_until;
    renderLookingButton();
    showToast(turningOn ? "You're visible as looking for 1 hour" : "Stopped looking", "success");
  } catch (e) {
    console.error(e);
    showToast("Could not update your status", "error");
  }
}

// ---- Block / report ----
async function blockPlayer(username, report) {
  let reason = null;
  if (report) {
    reason = prompt(`Report ${username}: what happened? (they will also be blocked)`);
    if (reason === null) return;
  } else if (!confirm(`Block ${username}? You won't see each other anymore.`)) {
    return;
  }
  try {
    const res = await authFetch(`${API_BASE}/block`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_user: username, game: GAME, report: !!report, reason })
    });
    if (!res.ok) throw new Error(`block failed: ${res.status}`);
    showToast(report ? "Reported and blocked" : "Blocked", "success");

    // remove from the current deck
    const key = String(username).toLowerCase();
    const before = state.matches.length;
    state.matches = state.matches.filter((m, i) => {
      const drop = (m.username || "").toLowerCase() === key;
      if (drop && i < state.currentMatchIndex) state.currentMatchIndex--;
      return !drop;
    });
    if (state.matches.length !== before) renderCard();

    refreshSquad({ silent: true }).catch(() => { });
    refreshPending();
  } catch (e) {
    console.error(e);
    showToast("Could not block this player", "error");
  }
}

function computeSquadSignature(squad) {
  // include everything the squad list shows
  return (squad || [])
    .map(m => `${(m.username || "").toLowerCase()}|${m.in_game_username || ""}|${m.discord_username || ""}|${m.looking_now ? 1 : 0}|${m.last_active || ""}`)
    .sort()
    .join(";");
}

function setLoading(isLoading, message = "Scanning for Operators...") {
  state.loading = !!isLoading;

  // Find Matches button
  if (els.btnFind) els.btnFind.disabled = !!isLoading;

  // Match card buttons
  const likeBtn = document.querySelector(".btn-like");
  const skipBtn = document.querySelector(".btn-skip");
  if (likeBtn) likeBtn.disabled = !!isLoading;
  if (skipBtn) skipBtn.disabled = !!isLoading;

  // Center message area
  if (els.cardWrapper && isLoading) {
    els.cardWrapper.innerHTML = `
  <div class="empty-state">
    <div class="scan-pulse"></div>
    <h3>${esc(message)}</h3>
    <p>Finding players that fit how you play…</p>
  </div>
`;
  }
}

/* =========================================================
   REALTIME (SINGLE TIMER) — Step 9E
========================================================= */
function canRealtimeRun() {
  const u = (state.profile.username || "").trim();
  if (!u) return false;
  if (document.visibilityState === "hidden") return false;
  return true;
}

async function realtimeTick({ silentSquad = true } = {}) {
  if (!canRealtimeRun()) return;

  // 1) Ping (guard)
  if (!inFlight.ping) {
    inFlight.ping = true;
    try {
      const token = getAccessToken();

      // اگر توکن نداریم، ping نزن (401 بی‌خودی تولید نکن)
      if (!token) {
        // هیچ
      } else {
        try {
          const res = await authFetch(`${API_BASE}/ping?game=${GAME}`, { method: "POST" });

          if (res.ok) {
            hideNetError();

            const data = await res.json().catch(() => null);

            const serverUsername = data?.username ? String(data.username).trim() : "";
            const serverDisplay = data?.display_username ? String(data.display_username).trim() : "";

            const effective = serverDisplay || serverUsername;

            if (effective) {
              // If localStorage has a different username, override it (token is source of truth)
              const localU = (localStorage.getItem("pm_username") || "").trim();
              if (localU && localU !== effective) {
                // اینجا اگر mismatch داری یعنی قبلاً token/username قاطی بوده
                // از این به بعد همیشه به نفع سرور درستش می‌کنیم
                localStorage.setItem("pm_username", effective);
              }

              setLockedUsername(effective);
              localStorage.setItem("pm_username_locked", "1");
            }

          }


        } catch (e) {
          // authFetch خودش redirect می‌کند اگر 401/بدون توکن
          // فقط اگر واقعاً شبکه down بود، banner را نشان بده
          showNetError();
        }

      }
    } catch {
      showNetError();
    } finally {
      inFlight.ping = false;
    }
  }


  // 2) Squad refresh (let refreshSquad manage inFlight.squad)
  try {
    await refreshSquad({ silent: !!silentSquad });

    // اگر refreshSquad بدون throw برگرده، یعنی ok
    hideNetError();
  } catch {
    showNetError();
  }

  // 3) Pending likes (someone may have liked me back -> moves to squad)
  refreshPending();
  renderLookingButton();

}


function startRealtime() {
  // prevent duplicate intervals
  if (realtimeTimer) return;

  // immediate tick once
  realtimeTick({ silentSquad: true });

  // single interval
  realtimeTimer = setInterval(() => realtimeTick({ silentSquad: true }), REALTIME_INTERVAL_MS);
}

function stopRealtime() {
  if (realtimeTimer) {
    clearInterval(realtimeTimer);
    realtimeTimer = null;
  }

  // reset guards (safe)
  inFlight.ping = false;
  inFlight.squad = false;
}

// // Legacy wrapper: keep for backward compatibility
// function setupHeartbeat() {
//   startRealtime();
// }


/* =========================================================
   PROFILE
========================================================= */
function setupEventListeners() {
  // Region -> City
  els.region.addEventListener("change", () => {
    els.city.innerHTML = `<option value="">Select City...</option>`;
    els.city.disabled = true;

    const regionData = (META?.regions || []).find(r => r.id === els.region.value);
    if (!regionData) return;

    els.city.disabled = false;
    (regionData.cities || []).forEach(c => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      els.city.appendChild(opt);
    });


  });

  // Looking for a squad now
  els.btnLooking?.addEventListener("click", toggleLooking);

  // Manual squad refresh
  const refreshBtn = document.getElementById("btn-refresh-squad");
  refreshBtn?.addEventListener("click", async () => {
    refreshBtn.classList.add("spinning");
    try {
      await refreshSquad({ silent: false });
      await refreshPending();
    } catch { } finally {
      refreshBtn.classList.remove("spinning");
    }
  });

  // Keyboard: ← skip, → like, Esc closes the modal
  document.addEventListener("keydown", (e) => {
    if (e.target instanceof Element && e.target.closest("input, select, textarea")) return;
    if (e.key === "Escape" && els.modal.classList.contains("active")) return closeModal();
    if (els.modal.classList.contains("active") || !document.getElementById("active-card")) return;
    if (e.key === "ArrowLeft") handleSkip();
    if (e.key === "ArrowRight") handleLike();
  });

  // Copy / block / report buttons (match card + squad list)
  document.addEventListener("click", (e) => {
    if (!(e.target instanceof Element)) return;
    const copyBtn = e.target.closest("[data-copy]");
    if (copyBtn) return copyText(copyBtn.dataset.copy, copyBtn.dataset.copyLabel || "Text");

    const blockBtn = e.target.closest("[data-block-user]");
    if (blockBtn) return blockPlayer(blockBtn.dataset.blockUser, false);

    const reportBtn = e.target.closest("[data-report-user]");
    if (reportBtn) return blockPlayer(reportBtn.dataset.reportUser, true);
  });

  // Find Matches action (shared by button click + Enter key submit)
  async function runFindMatches(e) {
    if (e) e.preventDefault();

    try {
      await saveProfile();     // 1) save first
    } catch {
      return;                  // save failed (toast already shown) -> don't scan
    }
    await findMatches();       // 2) then scan
  }

  // Click on button (won't submit the form anymore because type="button")
  els.btnFind.addEventListener("click", runFindMatches);

  // Pressing Enter inside the form still works (submit)
  els.form.addEventListener("submit", runFindMatches);

}

function updateStateLangs() {
  updateStateLangsFromPills(); // alias
}

function loadProfileFromStorage() {
  const stored = localStorage.getItem("playmate_profile");
  if (!stored) return;

  try {
    applyProfileToForm(JSON.parse(stored));
  } catch (e) {
    console.error("Error parsing profile", e);
  }
}

// Server is the source of truth: restores the profile on any browser/device
async function loadProfileFromServer() {
  try {
    const res = await authFetch(`${API_BASE}/my-profile?game=${GAME}`);
    if (res.status === 404) return false; // no profile saved yet
    if (!res.ok) return false;

    const data = await res.json();
    const toStore = {
      username: data.username,
      display_username: data.display_username || data.username,
      game: data.game || GAME,
      region: data.region,
      city: data.city || null,
      platform: data.platform,
      favorite_mode: data.favorite_mode,
      class_type: data.class_type,
      mic: data.mic,
      languages: data.languages || "",
      in_game_username: data.in_game_username || "",
      discord_username: data.discord_username || "",
      looking_until: data.looking_until || null,
      profile_pic_url: data.profile_pic_url || null,
      wallpaper_url: data.wallpaper_url || null,
      game_meta: data.game_meta || {}
    };
    localStorage.setItem("playmate_profile", JSON.stringify(toStore));
    applyProfileToForm(toStore);
    return true;
  } catch (e) {
    console.warn("Could not load profile from server", e);
    return false;
  }
}

function applyProfileToForm(data) {
  try {
    // state
    state.profile = { ...state.profile, ...data };

    // DOM
    setLockedUsername(data.display_username || data.username || "");
    els.ign.value = data.in_game_username || "";
    if (els.discord) els.discord.value = data.discord_username || "";
    if ("looking_until" in data) state.profile.looking_until = data.looking_until;
    renderLookingButton();
    // Region + City (normalize to META id)
    const normalizedRegion = normalizeRegionId(data.region || "");
    els.region.value = normalizedRegion;
    els.region.dispatchEvent(new Event("change")); // city options rebuild

    // بعد از rebuild، city را ست کن
    els.city.value = data.city || "";
    els.platform.value = data.platform || "PC";
    els.favoriteMode.value = data.favorite_mode || "Conquest";
    els.classType.value = data.class_type || "Assault";
    els.mic.value = data.mic || "voice";

    // langs (string "en,fa" or array)
    if (data.languages) {
      if (Array.isArray(data.languages)) state.profile.languages = data.languages;
      else state.profile.languages = String(data.languages).split(",").map(x => x.trim()).filter(Boolean);

      applyStoredLanguagesToPills();
    }

    els.status.textContent = `Profile loaded for '${state.profile.display_username || ""}'`;
    updateProfileLink(state.profile.username);
  } catch (e) {
    console.error("Error applying profile", e);
  }
}

async function saveProfile() {
  // state <- DOM
  const locked = (localStorage.getItem("pm_username") || "").trim();
  if (!locked) {
    showToast("No PlayMate Username found. Please go back to Landing and log in again.", "error");
    clearAuthAndRedirect();
    return;
  }

  setLockedUsername(locked); // keeps state/profile consistent

  state.profile.in_game_username = els.ign.value;
  state.profile.discord_username = els.discord ? els.discord.value : "";
  state.profile.region = els.region.value;
  state.profile.city = els.city.value || null;
  state.profile.platform = els.platform.value;
  state.profile.favorite_mode = els.favoriteMode.value;
  state.profile.class_type = els.classType.value;
  state.profile.mic = els.mic.value;
  updateStateLangs();

  const missing = [];
  if (!state.profile.region) missing.push("Region");
  if (!state.profile.favorite_mode) missing.push("Favorite Mode");
  if (!state.profile.class_type) missing.push("Class");
  if (!state.profile.mic) missing.push("Mic");
  if (!(state.profile.languages || []).length) missing.push("Languages");
  if (missing.length) {
    showToast(`Please fill in: ${missing.join(", ")}`, "error");
    throw new Error("Validation");
  }

  const payload = {
    username: locked,              // locked
    game: GAME,
    region: state.profile.region,
    city: state.profile.city || null,
    platform: state.profile.platform,
    favorite_mode: state.profile.favorite_mode,
    class_type: state.profile.class_type,
    mic: state.profile.mic,
    languages: (state.profile.languages || []).join(","),
    in_game_username: state.profile.in_game_username,
    discord_username: state.profile.discord_username || null,
    profile_pic_url: null,
    wallpaper_url: null,
    game_meta: {}
  };

  // Store both
  try {
    const res = await authFetch(`${API_BASE}/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });


    if (res.status === 409) {
      showToast("This Battlefield username is already used by another PlayMate user.", "error");
      throw new Error("Conflict");
    }
    if (!res.ok) {
      let msg = "Failed to save profile";
      try {
        const j = await res.json();
        if (typeof j?.detail === "string") msg = j.detail;
      } catch { }
      showToast(msg, "error");
      throw new Error("Conflict"); // already shown
    }

    // store local only after success
    localStorage.setItem("playmate_profile", JSON.stringify({
      ...payload, username: state.profile.username, display_username: state.profile.display_username
    }));
    updateProfileLink(state.profile.username);
    renderLookingButton();

    els.status.textContent = "Profile saved successfully!";
    showToast("Profile saved!", "success");

    startRealtime();
    if (els.usernameHidden) els.usernameHidden.disabled = true;
    localStorage.setItem("pm_username_locked", "1");

  } catch (err) {
    console.error(err);
    if (err.message !== "Conflict") showToast("Failed to save profile", "error");
    throw err;
  }
}

function updateProfileLink(username) {
  const a = els.viewProfileLink;
  if (!a) return;

  const u = (username || "").trim().toLowerCase();
  if (!u) {
    a.href = "#";
    a.style.display = "none";
    a.onclick = null;
    return;
  }

  a.href = "/profile?username=" + encodeURIComponent(u);
  a.style.display = "block";
  a.onclick = null;
}

/* =========================================================
   MATCHING
========================================================= */
async function findMatches() {
  if (state.loading) return;
  if (inFlight.match) return;

  inFlight.match = true;
  try {
    setLoading(true, "Scanning for Operators...");

    const res = await authFetch(`${API_BASE}/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: state.profile.username,
        game: GAME,
        region: els.region.value,
        city: els.city.value,
        favorite_mode: els.favoriteMode.value,
        class_type: els.classType.value,
        mic: els.mic.value,
        languages: (state.profile.languages || []).join(","),
        platform: els.platform.value || null,
        in_game_username: (els.ign.value || "").trim() || null,
        profile_pic_url: null,
        wallpaper_url: null,
        game_meta: {}
      })
    });

    if (!res.ok) {
      let msg = `match failed: ${res.status}`;
      try {
        const j = await res.json();
        if (j?.detail) msg = (typeof j.detail === "string") ? j.detail : JSON.stringify(j.detail);
      } catch { }
      throw new Error(msg);
    }

    const data = await res.json();
    state.matches = data.matches || [];
    state.currentMatchIndex = 0;

    if (!state.matches.length) {
      setLoading(false);
      els.cardWrapper.innerHTML = `
<div class="empty-state">
  <h3>No matches yet</h3>
  <p>Nobody new fits right now. Try another region, mode or language — or turn on
    <b>Looking for a squad</b> so others find you.</p>
  <div style="margin-top:18px;">
    <button class="btn-primary" type="button" onclick="findMatches()">Scan again</button>
  </div>
</div>
  `;
      return;
    }



    setLoading(false);
    renderCard();
  } catch (err) {
    console.error(err);
    showNetError();
    setLoading(false);
    showToast(err.message || "Could not fetch matches", "error");
  } finally {
    inFlight.match = false;
  }
}

function renderCard() {
  if (state.loading) return;

  if (!state.matches || state.currentMatchIndex >= state.matches.length) {
    els.cardWrapper.innerHTML = `
<div class="empty-state">
  <h3>You're all caught up</h3>
  <p>You've seen everyone for now. Check back later or change your preferences.</p>
  <div style="margin-top:18px;">
    <button class="btn-primary" type="button" onclick="findMatches()">Scan again</button>
  </div>
</div>
  `;
    return;
  }



  const match = state.matches[state.currentMatchIndex];
  const p = match.profile;

  const name = p.display_username || match.username;
  const pct = Math.max(0, Math.min(100, Number(match.match_percent) || 0));
  const circ = 2 * Math.PI * 34;
  const langs = langLabels(p.languages);
  const remaining = state.matches.length - state.currentMatchIndex;

  els.cardWrapper.innerHTML = `
<div class="card-stack">
  <div class="match-card" id="active-card">
    <div class="card-avatar"><div class="avatar-face" style="--hue:${avatarHue(name)}">${getInitials(name)}</div></div>

    <div class="match-percent" title="Match score">
      <svg viewBox="0 0 80 80">
        <circle class="ring-bg" cx="40" cy="40" r="34" fill="none" stroke-width="6"/>
        <circle class="ring-fg" cx="40" cy="40" r="34" fill="none" stroke-width="6"
          stroke-dasharray="${circ}" stroke-dashoffset="${circ * (1 - pct / 100)}"/>
      </svg>
      <div class="pct-label"><span class="pct-value">${pct}%</span><span class="pct-text">MATCH</span></div>
    </div>

    <div class="card-brand"><svg><use href="#i-logo"/></svg>PlayMate</div>
    <div class="player-name">${esc(name)}</div>
    ${match.looking_now ? '<div style="margin-top:8px;"><span class="looking-badge">● Looking for a squad now</span></div>' : ""}

    <div class="pill-container">
      <span class="info-pill">${svgIcon("globe")}Region: <b>${esc(regionLabel(p.region))}</b></span>
      ${p.favorite_mode ? `<span class="info-pill">${svgIcon("flag")}Mode: <b>${esc(p.favorite_mode)}</b></span>` : ""}
      <span class="info-pill">${svgIcon("class")}Class: <b>${esc(p.class_type)}</b></span>
      <span class="info-pill">${svgIcon("mic")}Mic: <b>${esc(MIC_LABELS[p.mic] || p.mic)}</b></span>
      ${p.platform ? `<span class="info-pill">${svgIcon("monitor")}<b>${esc(p.platform)}</b></span>` : ""}
      ${langs ? `<span class="info-pill">${svgIcon("chat")}Languages: <b>${esc(langs)}</b></span>` : ""}
    </div>

    <details class="match-reasons" open>
      <summary>Why this match</summary>
      <ul>${(match.reasons || []).map(r => `<li>${esc(r)}</li>`).join("")}</ul>
    </details>

    <div class="ign-row">
      <div class="ign-label">In-game username</div>
      <div class="ign-hidden">HIDDEN UNTIL MUTUAL LIKE</div>
    </div>
  </div>
</div>

<div class="actions">
  <div class="action-wrap">
    <button class="action-btn btn-skip" onclick="handleSkip()" aria-label="Skip" title="Skip (←)">${svgIcon("x")}</button>
    Skip
  </div>
  <div class="action-wrap">
    <button class="action-btn btn-like" onclick="handleLike()" aria-label="Add to squad" title="Add to squad (→)">${svgIcon("heart")}</button>
    Add to squad
  </div>
</div>

<div class="card-safety">
  <button type="button" data-block-user="${esc(match.username)}">Block</button>
  ·
  <button type="button" data-report-user="${esc(match.username)}">Report</button>
</div>
<div class="deck-counter">${remaining} player${remaining === 1 ? "" : "s"} left in this scan</div>
  `;
}

function handleSkip() {
  if (state.loading) return;

  const card = document.getElementById("active-card");
  if (!card) return;

  card.classList.add("swipe-left");
  setTimeout(() => {
    state.currentMatchIndex++;
    renderCard();
  }, 300);
}

async function handleLike() {
  if (state.loading) return;
  if (inFlight.like) return;

  inFlight.like = true;

  const likeBtn = document.querySelector(".btn-like");
  const skipBtn = document.querySelector(".btn-skip");
  likeBtn?.setAttribute("disabled", true);
  skipBtn?.setAttribute("disabled", true);

  const card = document.getElementById("active-card");
  const matchUser = state.matches[state.currentMatchIndex];

  // Guard: اگر کارت/یوزر نداریم، قفل نکن
  if (!matchUser) {
    likeBtn?.removeAttribute("disabled");
    skipBtn?.removeAttribute("disabled");
    inFlight.like = false;
    return;
  }

  // Optimistic UI
  if (card) card.classList.add("swipe-right");
  let liked = true;

  try {
    const res = await authFetch(`${API_BASE}/like`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        to_user: matchUser.username,
        game: GAME
      })

    });

    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      const msg =
        (data?.detail && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))) ||
        `Like failed: ${res.status}`;
      showToast(msg, "error");
      liked = false;
      return;
    }

    const isMutual = (data?.mutual === true || data?.status === "mutual");

    // matchUser از /api/match می‌آید و profile داخلش است
    const mp = matchUser.profile || {};
    const mate = {
      username: matchUser.username,
      display_username: mp.display_username || matchUser.username,
      in_game_username: null
    };

    if (isMutual) {
      // IGN is only revealed in the squad response -> refresh first, then show it.
      // Mark as known so refreshSquad doesn't open a second modal for the same person.
      const key = (matchUser.username || "").toLowerCase();
      lastSquadUsernames.add(key);
      try { await refreshSquad({ silent: true }); } catch { }
      refreshPending();
      const fromSquad = (state.squad || []).find(m => (m.username || "").toLowerCase() === key);
      if (fromSquad?.in_game_username) mate.in_game_username = fromSquad.in_game_username;
      triggerMatchModal(mate, { kind: "match" });
    } else {
      triggerMatchModal(mate, { kind: "like" });
      // squad را در پس‌زمینه رفرش کن
      refreshSquad().catch(() => { });
      refreshPending();
    }

  } catch (err) {
    console.error("Like failed", err);
    liked = false;
    showNetError();
    showToast("Connection error sending like", "error");
  } finally {
    // Always release the lock; only move to the next card if the like went through
    setTimeout(() => {
      if (liked) {
        state.currentMatchIndex++;
        renderCard();
      } else if (card) {
        card.classList.remove("swipe-right");
      }
      likeBtn?.removeAttribute("disabled");
      skipBtn?.removeAttribute("disabled");
      inFlight.like = false;
    }, 300);
  }
}

let lastSquadUsernames = new Set();
let squadBootstrapped = false; // prevents match modal on first load


/* =========================================================
   SQUAD + STATUS
========================================================= */
async function refreshSquad(opts = {}) {
  const silent = !!opts.silent;
  if (!state.profile.username) return;

  // NEW: if a squad fetch is already running, await it (no race)
  if (inFlight.squadPromise) {
    return await inFlight.squadPromise;
  }

  inFlight.squad = true;

  inFlight.squadPromise = (async () => {
    const res = await authFetch(
      `${API_BASE}/my-squad-details?game=${GAME}`
    );

    // 404 = this user has not saved a profile yet (not a connection problem)
    if (res.status === 404) {
      state.squad = [];
      renderSquadList({ silent });
      squadBootstrapped = true;
      return;
    }
    if (!res.ok) throw new Error(`squad failed: ${res.status}`);

    const data = await res.json();
    const newSquad = data.squadmates || [];

    // detect newly added squadmates (by username)
    const newSet = new Set(
      newSquad.map(m => (m.username || "").toLowerCase()).filter(Boolean)
    );
    const newlyAdded = [...newSet].filter(u => !lastSquadUsernames.has(u));
    lastSquadUsernames = newSet;

    // first successful refresh = baseline (no auto modal for existing squadmates)
    const wasBootstrapped = squadBootstrapped;
    squadBootstrapped = true;

    const sig = computeSquadSignature(newSquad);
    if (sig === lastSquadSignature) return;

    lastSquadSignature = sig;

    state.squad = newSquad;
    renderSquadList({ silent });


    // if a new squadmate arrived, show match modal automatically
    // BUT: never on first bootstrap refresh
    if (wasBootstrapped && newlyAdded.length) {
      const u = newlyAdded[0];
      const mate = newSquad.find(m => (m.username || "").toLowerCase() === u);
      if (mate) {
        triggerMatchModal({
          username: mate.username,
          display_username: mate.display_username || mate.username,
          in_game_username: mate.in_game_username || "—"
        });
      }
    }


  })();

  try {
    return await inFlight.squadPromise;
  } catch (err) {
    console.error("Squad fetch error", err);
    showNetError();
    throw err;
  } finally {
    inFlight.squad = false;
    inFlight.squadPromise = null;
  }
}



function renderSquadList({ silent = false } = {}) {
  // silent فعلاً استفاده نمی‌شود، ولی امضا درست است
  els.squadList.innerHTML = "";

  const countEl = document.getElementById("squad-count");
  if (countEl) countEl.textContent = state.squad?.length ? `(${state.squad.length})` : "";

  if (!state.squad || state.squad.length === 0) {
    els.squadList.innerHTML =
      '<div class="squad-empty">No squadmates yet. When you and another player both like each other, they show up here.</div>';
    return;
  }

  state.squad.forEach(mate => {
    const label = formatLastSeen(mate.last_active);

    const presence = presenceOf(mate.last_active);
    const statusText = mate.looking_now
      ? "Looking for a squad"
      : presence === "online" ? "Online" : presence === "away" ? "Away · " + label.replace("Last seen ", "") : label;

    const ign = mate.in_game_username || "";
    const discord = mate.discord_username || "";
    const name = mate.display_username || mate.username || "";

    const item = document.createElement("div");
    item.className = "squad-member";
    item.innerHTML = `
  <span class="status-dot ${mate.looking_now ? "online" : presence}"></span>
  <div class="sm-avatar avatar-face" style="--hue:${avatarHue(name)}">${getInitials(name)}</div>
  <div class="sm-info">
    <span class="sm-name">${esc(name)}</span>
    <span class="sm-status ${mate.looking_now ? "online" : presence}">${esc(statusText)}</span>
    <span class="sm-ign">In-game: <b>${esc(ign || "—")}</b>${discord ? `<br>Discord: <b>${esc(discord)}</b>` : ""}</span>
    <div class="sm-actions">
      ${ign ? `<button type="button" class="sm-btn" data-copy="${esc(ign)}" data-copy-label="In-game name">Copy in-game</button>` : ""}
      ${discord ? `<button type="button" class="sm-btn" data-copy="${esc(discord)}" data-copy-label="Discord">Copy Discord</button>` : ""}
      <button type="button" class="sm-btn danger" data-block-user="${esc(mate.username)}">Block</button>
    </div>
  </div>
`;
    els.squadList.appendChild(item);
  });
}

// People I liked who haven't liked me back yet
async function refreshPending() {
  if (!state.profile.username) return;
  if (inFlight.pending) return;
  inFlight.pending = true;
  try {
    const res = await authFetch(`${API_BASE}/pending-likes?game=${GAME}`);
    if (!res.ok) return; // 404 = no profile yet; pending is optional UI
    const data = await res.json();
    renderPendingList(data.pending || []);
  } catch (e) {
    console.warn("Pending likes fetch failed", e);
  } finally {
    inFlight.pending = false;
  }
}

function renderPendingList(list) {
  if (!els.pendingSection || !els.pendingList) return;

  if (!list.length) {
    els.pendingSection.style.display = "none";
    els.pendingList.innerHTML = "";
    return;
  }

  els.pendingSection.style.display = "";
  if (els.pendingCount) els.pendingCount.textContent = String(list.length);
  els.pendingList.innerHTML = "";

  list.forEach(p => {
    const name = p.display_username || p.username || "";
    const item = document.createElement("div");
    item.className = "squad-member pending";
    item.innerHTML = `
  <div class="sm-avatar avatar-face"></div>
  <div class="sm-info">
    <span class="sm-name"></span>
    <span class="sm-status">Waiting for them to like you back</span>
  </div>
`;
    paintAvatar(item.querySelector(".sm-avatar"), name);
    item.querySelector(".sm-name").textContent = name;
    els.pendingList.appendChild(item);
  });
}

function formatLastSeen(lastActiveIso) {
  if (!lastActiveIso) return "Last seen: unknown";

  const lastMs = new Date(lastActiveIso).getTime();
  if (!Number.isFinite(lastMs)) return "Last seen: unknown";

  const diffSec = Math.floor((Date.now() - lastMs) / 1000);

  if (diffSec < 0) return "Last seen: now";
  if (diffSec <= 60) return "Online";

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `Last seen ${diffMin}m ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `Last seen ${diffHr}h ago`;

  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `Last seen ${diffDay}d ago`;

  const diffYr = Math.floor(diffDay / 365);
  if (diffYr >= 1) return `Last seen ${diffYr}y ago`;

  const diffMon = Math.floor(diffDay / 30);
  return `Last seen ${diffMon}mo ago`;
}

/* =========================================================
   MODAL
========================================================= */
function goToSquad() {
  closeModal();
  const panel =
    document.querySelector(".panel-squad") ||
    document.getElementById("squad-panel") ||
    document.getElementById("squad-list");
  if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function triggerMatchModal(mate, opts = {}) {
  const kind = opts.kind || "match"; // "match" | "like"

  const meDisplay = state.profile.display_username || state.profile.username || "You";
  const meIGN = state.profile.in_game_username || "—";

  const mateDisplay = mate?.display_username || mate?.username || "User";
  const mateIGN = mate?.in_game_username || (kind === "like" ? "Hidden until match" : "—");

  // title/sub text
  const titleEl = document.getElementById("modal-title");
  const subEl = document.getElementById("modal-sub");

  if (titleEl && subEl) {
    if (kind === "like") {
      titleEl.textContent = "LIKE SENT";
      subEl.innerHTML = `You liked <span id="modal-them-name" style="color:#fff; font-weight:700;">${esc(mateDisplay)}</span>. If they like you back, you'll match.`;
    } else {
      titleEl.textContent = "IT'S A MATCH!";
      subEl.innerHTML = `You're now squadmates with <span id="modal-them-name" style="color:#fff; font-weight:700;">${esc(mateDisplay)}</span>!`;
    }
  }

  paintAvatar(document.getElementById("modal-me-avatar"), meDisplay);
  paintAvatar(document.getElementById("modal-them-avatar"), mateDisplay);

  // (این span را بالا در innerHTML ساختیم؛ حالا مطمئن می‌شویم درست set می‌شود)
  const themName = document.getElementById("modal-them-name");
  if (themName) themName.textContent = mateDisplay;

  document.getElementById("modal-me-name").textContent = meDisplay;
  document.getElementById("modal-me-ign").textContent = `In-game: ${meIGN}`;

  document.getElementById("modal-them-name-2").textContent = mateDisplay;
  document.getElementById("modal-them-ign").textContent = `In-game: ${mateIGN}`;

  // "like sent" has no energy link yet; a match does
  els.modal.classList.toggle("is-like", kind === "like");
  els.modal.classList.add("active");
}


window.closeModal = function () {
  els.modal.classList.remove("active");
};

/* =========================================================
   META (REGION/MODE/LANG)
========================================================= */
async function loadMeta() {
  const res = await fetch(`${API_BASE}/meta/${GAME}`);
  if (!res.ok) throw new Error(`meta failed: ${res.status}`);
  META = await res.json();
}

function populateRegions() {
  els.region.innerHTML = `<option value="">Select Region...</option>`;
  (META?.regions || []).forEach(r => {
    const opt = document.createElement("option");
    opt.value = r.id;          // e.g. na-west
    opt.textContent = r.label; // e.g. North America West
    els.region.appendChild(opt);
  });

  els.city.innerHTML = `<option value="">Select City...</option>`;
  els.city.disabled = true;
}

function populateFavoriteModes() {
  els.favoriteMode.innerHTML = `<option value="">Fav Mode...</option>`;
  (META?.favorite_modes || []).forEach(m => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    els.favoriteMode.appendChild(opt);
  });
}

function renderLanguagesFromMeta() {
  els.langContainer.innerHTML = "";
  (META?.languages || []).forEach(l => {
    const pill = document.createElement("div");
    pill.className = "lang-pill";
    pill.dataset.code = l.code;
    pill.textContent = l.label;

    pill.addEventListener("click", () => {
      pill.classList.toggle("active");
      updateStateLangsFromPills();
    });

    els.langContainer.appendChild(pill);
  });
}

function updateStateLangsFromPills() {
  const active = Array.from(els.langContainer.querySelectorAll(".lang-pill.active"));
  state.profile.languages = active.map(el => el.dataset.code);
}

function applyStoredLanguagesToPills() {
  const codes = new Set(state.profile.languages || []);
  els.langContainer.querySelectorAll(".lang-pill").forEach(p => {
    if (codes.has(p.dataset.code)) p.classList.add("active");
    else p.classList.remove("active");
  });
}
