/* =========================================================
   PlayMate — public player profile (/u/<username>)
   Anyone can view; the owner gets "Edit profile" (avatar, banner, bio, links).
========================================================= */

const API = "/api";
const SUPABASE_URL = "https://fffejwdrqhizgxpjacgn.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmZmVqd2RycWhpemd4cGphY2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTExNjgsImV4cCI6MjA4MDc4NzE2OH0.Zr2And6oP8PKmCDiW3rNcimBWh5cUV22YvnWwhQQz7s";
const sb = window.supabase?.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) || null;

const MIC_LABELS = { voice: "Voice", both: "Voice + Text", none: "No mic" };
const REGION_LABELS = {
  "na-west": "North America West", "na-east": "North America East", "eu-west": "Europe West",
  "eu-central": "Europe Central & East", "middle-east": "Middle East", "asia": "Asia", "oceania": "Oceania",
  "south-america": "Latin America", "africa": "Africa",
};
const LANG_LABELS = { en: "English", fa: "Persian", tr: "Turkish", ar: "Arabic", de: "German", fr: "French", es: "Spanish", ru: "Russian" };
const LINKS = {
  twitch: { icon: "twitch", label: "Twitch", url: h => `https://twitch.tv/${encodeURIComponent(h)}` },
  youtube: { icon: "youtube", label: "YouTube", url: h => `https://youtube.com/@${encodeURIComponent(h.replace(/^@/, ""))}` },
  instagram: { icon: "instagram", label: "Instagram", url: h => `https://instagram.com/${encodeURIComponent(h.replace(/^@/, ""))}` },
};

const $ = (id) => document.getElementById(id);
const page = { data: null, isOwner: false, account: null, tab: "games", squadGame: null, rel: null };

/* ---------------- helpers ---------------- */
function esc(v) {
  return String(v ?? "").replace(/[&<>"'`]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;" })[ch]);
}
function icon(id) { return `<svg class="icon"><use href="#i-${id}"/></svg>`; }
function hue(name) {
  let h = 0;
  for (const ch of String(name || "").toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}
function initial(name) { return (String(name || "?").trim()[0] || "?").toUpperCase(); }
function toast(msg, type = "info") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  $("toast-container").appendChild(t);
  setTimeout(() => t.remove(), 3200);
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
  return res;
}

function lastSeenText(iso) {
  const t = iso ? new Date(iso).getTime() : NaN;
  if (!Number.isFinite(t)) return "Offline";
  const s = (Date.now() - t) / 1000;
  if (s <= 60) return "Online now";
  const m = Math.floor(s / 60);
  if (m < 60) return `Active ${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `Active ${h}h ago`;
  const d = Math.floor(h / 24);
  return d < 30 ? `Active ${d}d ago` : `Active ${Math.floor(d / 30)}mo ago`;
}

// avatar-1..12 are our SVG art, avatar-13 and up are illustrated WebP images
const AVATAR_COUNT = 25;
function avatarSrc(id) {
  const n = Number(String(id).split("-")[1]);
  return `/static/img/avatars/${id}.${n > 12 ? "webp" : "svg"}`;
}

function avatarHtml(d, cls = "pp-avatar") {
  const name = d.display_username || d.username;
  return d.avatar
    ? `<div class="${cls}"><img src="${esc(avatarSrc(d.avatar))}" alt=""></div>`
    : `<div class="${cls}"><div class="avatar-face" style="--hue:${hue(name)}">${esc(initial(name))}</div></div>`;
}

function usernameFromUrl() {
  const m = location.pathname.match(/^\/u\/([^/]+)/);
  if (m) return decodeURIComponent(m[1]);
  return new URLSearchParams(location.search).get("username") || "";
}

/* ---------------- render ---------------- */
function render() {
  const d = page.data;
  const name = d.display_username || d.username;
  document.title = `${name} | PlayMate`;
  const since = d.member_since ? new Date(d.member_since).toLocaleDateString("en", { month: "short", year: "numeric" }) : "";
  const earned = (d.badges || []).filter(b => b.earned);
  const links = Object.entries(d.links || {}).filter(([k, v]) => LINKS[k] && v);

  $("pp-main").innerHTML = `
    <section class="pp-hero">
      <div class="pp-banner"><img src="/static/img/banners/${esc(d.banner || "banner-1")}.svg" alt=""></div>
      <div class="pp-head">
        ${avatarHtml(d)}
        <div class="pp-id">
          <h1 class="pp-name">${esc(name)} ${earned.slice(0, 3).map(b => `<img class="pp-badge-mini" src="/static/img/badges/${esc(b.id)}.svg" alt="${esc(b.label)}" title="${esc(b.label)}">`).join("")}</h1>
          <div class="pp-handle">@${esc(d.username)}</div>
          <div class="pp-meta">
            <span class="pp-presence ${d.looking_now ? "looking" : lastSeenText(d.last_active) === "Online now" ? "online" : ""}">
              <span class="dot"></span>${d.looking_now ? "Looking for a squad now" : esc(lastSeenText(d.last_active))}</span>
            ${since ? `<span>${icon("calendar")}Member since ${esc(since)}</span>` : ""}
            <span>${icon("users")}${d.squad_count} squadmate${d.squad_count === 1 ? "" : "s"}</span>
          </div>
        </div>
        <div class="pp-actions">
          ${page.isOwner
      ? `<button type="button" class="btn-secondary" id="btn-edit">${icon("edit")}Edit profile</button>`
      : `<a class="btn-primary pp-cta" href="/app${d.games[0] ? `?game=${encodeURIComponent(d.games[0].id)}` : ""}">Find a squad ${icon("arrow")}</a>`}
          <button type="button" class="btn-secondary" id="btn-share">${icon("share")}Share</button>
        </div>
      </div>
      ${d.bio || page.isOwner ? `<p class="pp-bio ${d.bio ? "" : "empty"}">${d.bio ? esc(d.bio) : "Add a short bio so squadmates know how you play →"}</p>` : ""}
      ${links.length ? `<div class="pp-links">${links.map(([k, v]) => `<a href="${LINKS[k].url(v)}" target="_blank" rel="noopener nofollow">${icon(LINKS[k].icon)}${esc(v)}</a>`).join("")}</div>` : ""}
    </section>

    <nav class="pp-tabs" role="tablist">
      ${["games", "achievements", "squad"].map(t => `<button type="button" role="tab" data-tab="${t}" aria-selected="${page.tab === t}" aria-controls="pp-tab-body" class="${page.tab === t ? "active" : ""}">${t[0].toUpperCase() + t.slice(1)}${t === "games" ? ` <span class="count">${d.games.length}</span>` : t === "achievements" ? ` <span class="count">${earned.length}/${(d.badges || []).length}</span>` : ""}</button>`).join("")}
    </nav>
    <section class="pp-tab-body" id="pp-tab-body" role="tabpanel"></section>`;

  renderTab();
}

// Like / Like back from someone's public profile (state from /api/relationship; the server enforces everything)
function relAction(g) {
  const state = page.rel?.[g.id];
  if (!state) return "";
  const app = `/app?game=${encodeURIComponent(g.id)}`;
  switch (state) {
    case "none": return `<button type="button" class="pp-like" data-like-game="${esc(g.id)}">💚 Like in ${esc(g.name)}</button>`;
    case "likes_you": return `<button type="button" class="pp-like hot" data-like-game="${esc(g.id)}">💚 Like back — they like you</button>`;
    case "liked": return `<span class="pp-rel">Like sent ✓ — waiting for them</span>`;
    case "mutual": return `<a class="pp-like" href="${app}">✓ In your squad — open it</a>`;
    case "incompatible": return `<span class="pp-rel">You can't play together (platform, edition or server)</span>`;
    case "no_profile": return `<a class="pp-rel" href="${app}">Add ${esc(g.name)} to your games to like them →</a>`;
    default: return "";
  }
}

async function loadRelationship() {
  if (!token() || page.isOwner || !page.account?.username || !page.data) return;
  try {
    const res = await authFetch(`${API}/relationship?username=${encodeURIComponent(page.data.username)}`);
    if (res.ok) page.rel = (await res.json()).games || null;
  } catch { }
}

async function likeFromProfile(game, btn) {
  btn.disabled = true;
  try {
    const res = await authFetch(`${API}/like`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_user: page.data.username, game }),
    });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Could not send like");
    toast(d.mutual ? "It's a match! Their contact is in your squad." : "Like sent — you'll match if they like you back", "success");
    await loadRelationship();
    renderTab();
  } catch (e) {
    btn.disabled = false;
    if (e.message !== "AUTH_SWITCHED") toast(e.message || "Could not send like", "error");
  }
}

function renderTab() {
  const d = page.data;
  const body = $("pp-tab-body");
  document.querySelectorAll(".pp-tabs button").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === page.tab);
    b.setAttribute("aria-selected", String(b.dataset.tab === page.tab));
  });

  if (page.tab === "games") {
    body.innerHTML = `<div class="pp-games">
      ${d.games.map(g => {
      const fields = Object.entries(g.fields || {});
      const langs = String(g.languages || "").split(",").filter(Boolean).map(c => LANG_LABELS[c] || c).join(", ");
      return `
          <article class="pp-game" style="--accent:${esc(g.accent)}">
            <img class="pp-game-cover" src="${esc(g.cover)}" alt="" data-fallback="${esc(g.art || "/static/img/games/default.svg")}">
            <div class="pp-game-body">
              <h3>${esc(g.name)} ${g.looking_now ? '<span class="looking-badge">● Looking now</span>' : ""}</h3>
              <div class="pp-game-pills">
                ${g.region ? `<span class="info-pill">${icon("globe")}<b>${esc(REGION_LABELS[g.region] || g.region)}</b>${g.country ? ` · ${esc(g.country)}` : ""}</span>` : ""}
                ${fields.map(([, v]) => `<span class="info-pill"><b>${esc(v)}</b></span>`).join("")}
                ${g.platform ? `<span class="info-pill">${icon("monitor")}<b>${esc(g.platform)}</b></span>` : ""}
                ${g.mic ? `<span class="info-pill">${icon("mic")}<b>${esc(MIC_LABELS[g.mic] || g.mic)}</b></span>` : ""}
                ${langs ? `<span class="info-pill">${icon("chat")}<b>${esc(langs)}</b></span>` : ""}
              </div>
              <div class="pp-game-foot">
                <a class="pp-game-link" href="/app?game=${encodeURIComponent(g.id)}">${page.isOwner ? "Open in Find squad" : "Find a squad in this game"} ${icon("arrow")}</a>
                ${page.isOwner ? `<button type="button" class="pp-game-remove" data-remove-game="${esc(g.id)}" data-game-name="${esc(g.name)}">Remove</button>` : relAction(g)}
              </div>
            </div>
          </article>`;
    }).join("")}
      ${page.isOwner ? `<a class="pp-game add" href="/app?pick=1"><span class="pp-add-plus">+</span><span>Add another game</span></a>` : ""}
      ${!d.games.length && !page.isOwner ? `<p class="pp-empty">No games yet.</p>` : ""}
    </div>`;
  }

  if (page.tab === "achievements") {
    body.innerHTML = `<div class="pp-badges">
      ${(d.badges || []).map(b => `
        <div class="pp-badge ${b.earned ? "earned" : "locked"}">
          <img src="/static/img/badges/${b.earned ? esc(b.id) : "locked"}.svg" alt="">
          <div><b>${esc(b.label)}</b><span>${esc(b.earned ? b.desc : (b.desc === "Coming soon" ? "Coming soon" : "Locked · " + b.desc))}</span></div>
        </div>`).join("")}
    </div>`;
  }

  if (page.tab === "squad") {
    if (!d.games.length) {
      body.innerHTML = `<p class="pp-empty">No squad yet.</p>`;
      return;
    }
    page.squadGame = page.squadGame || d.games[0].id;
    body.innerHTML = `
      <div class="pp-squad-games">${d.games.map(g => `<button type="button" data-squad-game="${esc(g.id)}" class="${g.id === page.squadGame ? "active" : ""}"><img src="${esc(g.icon)}" alt="">${esc(g.name)}</button>`).join("")}</div>
      <div class="pp-squad" id="pp-squad"><div class="scan-pulse small"></div></div>`;
    loadSquad();
  }
}

async function loadSquad() {
  const box = $("pp-squad");
  try {
    const url = `/profile-squad?username=${encodeURIComponent(page.data.username)}&game=${encodeURIComponent(page.squadGame)}`;
    const res = token() ? await authFetch(url) : await fetch(url);   // logged in: hides players blocked either way
    const mates = (await res.json()).squadmates || [];
    box.innerHTML = mates.length
      ? mates.map(m => {
        const n = m.display_username || m.username;
        return `<a class="pp-mate" href="/u/${encodeURIComponent(m.username)}">
            <div class="avatar-face" style="--hue:${hue(n)}">${esc(initial(n))}</div>
            <div><b>${esc(n)}</b><span>${esc(REGION_LABELS[m.region] || m.region || "")}</span></div>
          </a>`;
      }).join("")
      : `<p class="pp-empty">No squadmates in this game yet.</p>`;
  } catch {
    box.innerHTML = `<p class="pp-empty">Could not load the squad.</p>`;
  }
}

/* ---------------- edit (owner) ---------------- */
function openEdit() {
  const a = page.account;
  // newest (illustrated) avatars first
  const avatars = Array.from({ length: AVATAR_COUNT }, (_, i) => `avatar-${AVATAR_COUNT - i}`);
  const banners = Array.from({ length: 8 }, (_, i) => `banner-${i + 1}`);
  const name = page.data.display_username || page.data.username;

  $("avatar-pick").innerHTML =
    `<button type="button" data-avatar="" class="${!a.avatar ? "active" : ""}" title="Initial" aria-label="Use my initial" aria-pressed="${!a.avatar}"><div class="avatar-face" style="--hue:${hue(name)}">${esc(initial(name))}</div></button>` +
    avatars.map(id => `<button type="button" data-avatar="${id}" class="${a.avatar === id ? "active" : ""}" aria-label="Avatar ${id.split("-")[1]}" aria-pressed="${a.avatar === id}"><img src="${avatarSrc(id)}" alt="" loading="lazy"></button>`).join("");
  $("banner-pick").innerHTML = banners.map(id =>
    `<button type="button" data-banner="${id}" class="${a.banner === id ? "active" : ""}" aria-label="Banner ${id.split("-")[1]}" aria-pressed="${a.banner === id}"><img src="/static/img/banners/${id}.svg" alt=""></button>`).join("");
  $("edit-bio").value = a.bio || "";
  $("bio-count").textContent = `${(a.bio || "").length}/280`;
  ["twitch", "youtube", "instagram"].forEach(k => { $(`link-${k}`).value = (a.links || {})[k] || ""; });
  $("edit-modal").classList.add("active");
}

function closeEdit() { $("edit-modal").classList.remove("active"); }

async function saveEdit() {
  const body = {
    bio: $("edit-bio").value.trim(),
    avatar: $("avatar-pick").querySelector(".active")?.dataset.avatar ?? "",
    banner: $("banner-pick").querySelector(".active")?.dataset.banner || "banner-1",
    links: Object.fromEntries(["twitch", "youtube", "instagram"].map(k => [k, $(`link-${k}`).value.trim()])),
  };
  const btn = $("edit-save");
  btn.disabled = true;
  try {
    const res = await authFetch(`${API}/account`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not save");
    page.account = data;
    Object.assign(page.data, { bio: data.bio, avatar: data.avatar, banner: data.banner, links: data.links });
    closeEdit();
    render();
    toast("Profile updated", "success");
  } catch (e) {
    toast(e.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function removeGame(gameId, name) {
  if (!confirm(`Remove ${name} from your profile? Your ${name} likes and squad will be removed too.`)) return;
  try {
    const res = await authFetch(`${API}/profile?game=${encodeURIComponent(gameId)}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Could not remove this game");
    page.data.games = page.data.games.filter(g => g.id !== gameId);
    if (localStorage.getItem("pm_game") === gameId) localStorage.removeItem("pm_game");
    render();
    toast(`${name} removed`, "success");
  } catch (e) {
    toast(e.message, "error");
  }
}

// broken cover image -> our own SVG art (data-fallback); no inline onerror, so the CSP needs no 'unsafe-inline'
document.addEventListener("error", (e) => {
  const img = e.target;
  if (img instanceof HTMLImageElement && img.dataset.fallback && !img.src.endsWith(img.dataset.fallback)) {
    img.src = img.dataset.fallback;
    delete img.dataset.fallback;
  }
}, true);

/* ---------------- events ---------------- */
document.addEventListener("click", async (e) => {
  if (!(e.target instanceof Element)) return;
  const t = e.target;
  const tab = t.closest(".pp-tabs [data-tab]");
  if (tab) { page.tab = tab.dataset.tab; return renderTab(); }
  const sg = t.closest("[data-squad-game]");
  if (sg) { page.squadGame = sg.dataset.squadGame; return renderTab(); }
  if (t.closest("#btn-edit") || t.closest(".pp-bio.empty")) return page.isOwner && openEdit();
  if (t.closest("#btn-share")) {
    const url = `${location.origin}/u/${encodeURIComponent(page.data.username)}`;
    try {
      if (navigator.share) await navigator.share({ title: `${page.data.display_username} on PlayMate`, url });
      else { await navigator.clipboard.writeText(url); toast("Profile link copied", "success"); }
    } catch { }
    return;
  }
  const av = t.closest("[data-avatar]");
  if (av) { $("avatar-pick").querySelectorAll("button").forEach(b => { b.classList.toggle("active", b === av); b.setAttribute("aria-pressed", String(b === av)); }); return; }
  const bn = t.closest("[data-banner]");
  if (bn) { $("banner-pick").querySelectorAll("button").forEach(b => { b.classList.toggle("active", b === bn); b.setAttribute("aria-pressed", String(b === bn)); }); return; }
  if (t.closest("#edit-close") || t.closest("#edit-cancel") || t === $("edit-modal")) return closeEdit();
  if (t.closest("#edit-save")) return saveEdit();
  const lk = t.closest("[data-like-game]");
  if (lk && !page.isOwner) return likeFromProfile(lk.dataset.likeGame, lk);
  const rm = t.closest("[data-remove-game]");
  if (rm && page.isOwner) return removeGame(rm.dataset.removeGame, rm.dataset.gameName);
});
document.addEventListener("keydown", e => { if (e.key === "Escape") closeEdit(); });
$("edit-bio").addEventListener("input", () => { $("bio-count").textContent = `${$("edit-bio").value.length}/280`; });

/* ---------------- init ---------------- */
(async function init() {
  const username = usernameFromUrl().trim();
  if (!username) {
    $("pp-main").innerHTML = `<div class="pp-loading"><h2>No player selected</h2><p><a class="profile-link" href="/app">Go to Find squad →</a></p></div>`;
    return;
  }

  // is the viewer logged in, and is this their own profile?
  if (token()) {
    $("nav-cta").textContent = "Find squad";
    $("nav-cta").href = "/app";
    try {
      const res = await authFetch(`${API}/account`);
      if (res.ok) {
        page.account = await res.json();
        if (page.account.username) $("nav-my-profile").href = `/u/${encodeURIComponent(page.account.username)}`;
        page.isOwner = (page.account.username || "") === username.toLowerCase();
      }
    } catch { }
  }
  if (!page.account?.username) $("nav-my-profile").style.display = "none";
  if (page.account) $("nav-settings").hidden = false;
  if (page.isOwner) $("nav-my-profile").classList.add("active");

  try {
    const url = `${API}/public-profile?username=${encodeURIComponent(username)}`;
    const res = token() ? await authFetch(url) : await fetch(url);
    if (res.status === 404) {
      $("pp-main").innerHTML = `<div class="pp-loading"><h2>Player not found</h2><p>No PlayMate player called “${esc(username)}”.</p><p><a class="profile-link" href="/app">Find a squad →</a></p></div>`;
      return;
    }
    page.data = await res.json();
    await loadRelationship();
    render();
  } catch {
    $("pp-main").innerHTML = `<div class="pp-loading"><h2>Could not load this profile</h2><p>Check your connection and try again.</p></div>`;
  }
})();
