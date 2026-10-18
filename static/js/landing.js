/* =========================================================
   PlayMate — landing page: games showcase + Supabase auth
========================================================= */
const SUPABASE_URL = "https://fffejwdrqhizgxpjacgn.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmZmVqd2RycWhpemd4cGphY2duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTExNjgsImV4cCI6MjA4MDc4NzE2OH0.Zr2And6oP8PKmCDiW3rNcimBWh5cUV22YvnWwhQQz7s";
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const USERNAME_RE = /^[A-Za-z0-9_.\-]{3,24}$/;
const $ = (id) => document.getElementById(id);
let AUTH_MODE = "login";
let recovering = false;

function esc(v) {
  return String(v ?? "").replace(/[&<>"'`]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;" })[ch]);
}

function goToApp() {
  window.location.href = "/app";
}

function storeSession(session) {
  localStorage.setItem("pm_access_token", session.access_token);
  const u = session.user?.user_metadata?.pm_username || session.user?.user_metadata?.username || "";
  if (u) localStorage.setItem("pm_username", u);
}

/* ---------------- referral (?ref=username) ---------------- */
(function captureRef() {
  const ref = new URLSearchParams(location.search).get("ref");
  if (ref && USERNAME_RE.test(ref)) {
    localStorage.setItem("pm_ref", ref.toLowerCase());
    $("ref-note").hidden = false;
    $("ref-note").innerHTML = `🎮 <b>${esc(ref)}</b> invited you to PlayMate`;
  }
})();

/* ---------------- already logged in? ---------------- */
supabaseClient.auth.onAuthStateChange((event, session) => {
  if (event === "PASSWORD_RECOVERY") {
    recovering = true;
    showRecovery();
  }
});

(async () => {
  try {
    const { data } = await supabaseClient.auth.getSession(); // also handles email-confirm redirects
    if (data?.session?.access_token && !recovering && !location.hash.includes("type=recovery")) {
      storeSession(data.session);
      goToApp();
    }
  } catch (e) {
    console.warn("session init failed:", e);
  }
})();

/* ---------------- auth form ---------------- */
function setError(msg) {
  $("auth-ok").hidden = true;
  $("auth-error").hidden = !msg;
  $("auth-error").textContent = msg || "";
}

function setOk(msg) {
  $("auth-error").hidden = true;
  $("auth-ok").hidden = !msg;
  $("auth-ok").textContent = msg || "";
}

function setAuthMode(mode) {
  AUTH_MODE = mode;
  const signup = mode === "signup";
  $("mode-login").classList.toggle("active", !signup);
  $("mode-signup").classList.toggle("active", signup);
  $("pm-username-group").hidden = !signup;
  $("authTitle").textContent = signup ? "Create your account" : "Welcome back";
  $("authSubtitle").textContent = signup ? "Free forever. Takes 20 seconds." : "Log in to find your squad.";
  $("auth-submit").textContent = signup ? "Create account" : "Log in";
  $("password").autocomplete = signup ? "new-password" : "current-password";
  $("forgot-btn").hidden = signup;
  setError("");
  setOk("");
}

async function handleAuth(e) {
  e.preventDefault();
  if (recovering) return saveNewPassword();

  const email = $("email").value.trim();
  const password = $("password").value;
  const username = $("pm_username").value.trim();
  const btn = $("auth-submit");

  if (!email || !/^\S+@\S+\.\S+$/.test(email)) return setError("Enter a valid email address.");
  if (password.length < 6) return setError("Password must be at least 6 characters.");
  if (AUTH_MODE === "signup" && !USERNAME_RE.test(username)) {
    return setError("Username: 3–24 letters, numbers, _ . or -");
  }

  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = AUTH_MODE === "signup" ? "Creating account…" : "Logging in…";
  setError("");

  try {
    let data;
    if (AUTH_MODE === "login") {
      const res = await supabaseClient.auth.signInWithPassword({ email, password });
      if (res.error) return setError(res.error.message === "Invalid login credentials" ? "Wrong email or password." : res.error.message);
      data = res.data;
    } else {
      const res = await supabaseClient.auth.signUp({
        email,
        password,
        options: { data: { pm_username: username }, emailRedirectTo: `${location.origin}/` },
      });
      if (res.error) return setError(res.error.message);
      data = res.data;
      if (!data.session) {
        setAuthMode("login");
        $("email").value = email;
        return setOk("Account created! Check your email to confirm, then log in.");
      }
    }
    if (!data?.session?.access_token) return setError("Something went wrong. Please try again.");
    storeSession(data.session);
    if (AUTH_MODE === "signup") localStorage.setItem("pm_username", username);
    goToApp();
  } catch {
    setError("Network error. Check your connection and try again.");
  } finally {
    btn.disabled = false;
    btn.textContent = label;
  }
}

async function forgotPassword() {
  const email = $("email").value.trim();
  if (!/^\S+@\S+\.\S+$/.test(email)) return setError("Type your email above first, then tap “Forgot password?”.");
  const { error } = await supabaseClient.auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/` });
  if (error) return setError(error.message);
  setOk("If that email has an account, a reset link is on its way.");
}

function showRecovery() {
  setAuthMode("login");
  $("authTitle").textContent = "Choose a new password";
  $("authSubtitle").textContent = "Enter a new password for your account.";
  $("email").closest(".form-group").hidden = true;
  $("forgot-btn").hidden = true;
  $("auth-submit").textContent = "Save new password";
  $("password").autocomplete = "new-password";
  $("password").value = "";
  document.getElementById("auth").scrollIntoView({ behavior: "smooth" });
}

async function saveNewPassword() {
  const password = $("password").value;
  if (password.length < 6) return setError("Password must be at least 6 characters.");
  const { data, error } = await supabaseClient.auth.updateUser({ password });
  if (error) return setError(error.message);
  const { data: s } = await supabaseClient.auth.getSession();
  if (s?.session) storeSession(s.session);
  setOk("Password updated. Taking you in…");
  setTimeout(goToApp, 800);
}

/* ---------------- games showcase ---------------- */
async function loadGames() {
  try {
    const res = await fetch("/api/games");
    const games = (await res.json()).games || [];
    $("lp-games").innerHTML = games.map(g => `
      <a class="lp-game" href="#auth" data-mode="signup" style="--accent:${esc(g.accent)}">
        <img src="${esc(g.cover)}" alt="${esc(g.name)} — ${esc(g.genre)}" loading="lazy" onerror="this.onerror=null;this.src='${esc(g.art || "/static/img/games/default.svg")}'">
      </a>`).join("");
    const covers = games.map(g => `<img src="${esc(g.cover)}" alt="">`).join("");
    $("lp-marquee").innerHTML = covers + covers;
    const total = games.reduce((n, g) => n + (g.players || 0), 0);
    if (total >= 50) $("lp-stat").textContent = `${total} player profiles across ${games.length} games — and growing.`;
  } catch { }
}

/* ---------------- events ---------------- */
$("mode-login").addEventListener("click", () => setAuthMode("login"));
$("mode-signup").addEventListener("click", () => setAuthMode("signup"));
$("authForm").addEventListener("submit", handleAuth);
$("forgot-btn").addEventListener("click", forgotPassword);
$("pw-toggle").addEventListener("click", () => {
  const p = $("password");
  p.type = p.type === "password" ? "text" : "password";
});
document.addEventListener("click", (e) => {
  const link = e.target instanceof Element && e.target.closest("[data-mode]");
  if (!link) return;
  e.preventDefault();
  setAuthMode(link.dataset.mode);
  $("auth").scrollIntoView({ behavior: "smooth", block: "center" });
  setTimeout(() => (link.dataset.mode === "signup" ? $("pm_username") : $("email")).focus(), 350);
});
$("year").textContent = new Date().getFullYear();

setAuthMode(new URLSearchParams(location.search).get("ref") ? "signup" : "login");
loadGames();
