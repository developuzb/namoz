// TAQVIMbot Mini App — vanilla JS
// Telegram WebApp API: window.Telegram.WebApp

const tg = window.Telegram?.WebApp;
const PRAYER_ICONS = {
  Bomdod: "🌅",
  Quyosh: "🌄",
  Peshin: "🌞",
  Asr: "🌤",
  Shom: "🌇",
  Xufton: "🌙",
};
const FARZ_NAMES = ["Bomdod", "Peshin", "Asr", "Shom", "Xufton"];

// State
const state = {
  user: null,
  subscriptions: [],
  currentRegion: null,
  currentTimes: null,
  currentDate: new Date(),
  countdownTimer: null,
};

// ============== Init ==============
async function init() {
  if (tg) {
    tg.ready();
    tg.expand();
    tg.MainButton.hide();
  }

  try {
    // Load user info
    const meRes = await fetchJSON(buildUrl("/api/me"));
    state.user = meRes.user;
    state.subscriptions = meRes.subscriptions || [];

    if (state.subscriptions.length === 0) {
      showError(
        "Hech qaysi hududga obuna emassiz. Avval botda /start bosib hudud tanlang."
      );
      return;
    }

    state.currentRegion = state.subscriptions[0];
    await loadTimesForDate(state.currentDate);
    setupDateNav();
  } catch (e) {
    console.error(e);
    showError(e.message || "Yuklab bo'lmadi");
  }
}

// ============== Date navigation ==============
function setupDateNav() {
  document.getElementById("btn-prev-day").onclick = () => {
    state.currentDate = new Date(state.currentDate.getTime() - 86400000);
    loadTimesForDate(state.currentDate);
  };
  document.getElementById("btn-next-day").onclick = () => {
    state.currentDate = new Date(state.currentDate.getTime() + 86400000);
    loadTimesForDate(state.currentDate);
  };
  document.getElementById("btn-today").onclick = () => {
    state.currentDate = new Date();
    loadTimesForDate(state.currentDate);
  };
}

// ============== Load times ==============
async function loadTimesForDate(d) {
  showLoading(true);
  try {
    const iso = toISODate(d);
    const url = buildUrl(
      `/api/times?region_id=${state.currentRegion.region_id}&date=${iso}`
    );
    const data = await fetchJSON(url);
    state.currentTimes = data;
    renderTimes(data);

    if (state.currentRegion.latitude && state.currentRegion.longitude) {
      const q = await fetchJSON(
        buildUrl(
          `/api/qibla?lat=${state.currentRegion.latitude}&lon=${state.currentRegion.longitude}`
        )
      );
      renderQibla(q);
    }

    document.getElementById("app").classList.remove("hidden");
    document.getElementById("loading").classList.add("hidden");
  } catch (e) {
    showError(e.message || "Vaqtlar olinmadi");
  }
}

// ============== Render ==============
function renderTimes(data) {
  document.getElementById("city-name").textContent = data.region.name.toUpperCase();

  // Sanalar
  const d = new Date(data.date);
  const dStr = `${d.getDate()}-${["yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentyabr","oktyabr","noyabr","dekabr"][d.getMonth()]}, ${d.getFullYear()}`;
  document.getElementById("dates").textContent = `${dStr}  ·  ${data.hijri}`;

  // Prayer list
  const list = document.getElementById("prayer-list");
  list.innerHTML = "";
  const now = new Date();
  const isToday = data.date === toISODate(now);

  ["Bomdod", "Quyosh", "Peshin", "Asr", "Shom", "Xufton"].forEach((p) => {
    const t = data.times[p] || "—";
    const row = document.createElement("div");
    row.className = "prayer-row";

    let cls = "";
    if (isToday && t !== "—") {
      const [hh, mm] = t.split(":").map(Number);
      const ptDate = new Date(now);
      ptDate.setHours(hh, mm, 0, 0);
      if (ptDate < now) cls = "passed";
    }
    if (cls) row.classList.add(cls);

    row.innerHTML = `
      <span class="icon">${PRAYER_ICONS[p] || "🕌"}</span>
      <span class="name">${p}</span>
      <span class="time">${t}</span>
    `;
    list.appendChild(row);
  });

  // Hero — next farz
  if (isToday) {
    updateNextFarz(data.times);
    startCountdown(data.times);
  } else {
    // Boshqa kun — countdown yo'q
    document.getElementById("next-name").textContent = "—";
    document.getElementById("next-time").textContent = "--:--";
    document.getElementById("countdown").textContent = "";
    if (state.countdownTimer) clearInterval(state.countdownTimer);
  }

  // Ayat
  if (data.ayah) {
    document.getElementById("ayah-arabic").textContent = data.ayah.arabic;
    document.getElementById("ayah-uzbek").textContent = `«${data.ayah.uzbek}»`;
    document.getElementById("ayah-ref").textContent = data.ayah.ref;
  }

  // Provider attribution
  const attr = {
    islomapi: "islomapi.uz · O'zbekiston musulmonlari idorasi",
    praytime: "praytime.uz",
    aladhan: "Aladhan API · ISNA · Hanafi",
  };
  document.getElementById("provider-attr").textContent = attr[data.provider] || data.provider;
}

function updateNextFarz(times) {
  const now = new Date();
  let next = null;
  for (const p of FARZ_NAMES) {
    const t = times[p];
    if (!t) continue;
    const [hh, mm] = t.split(":").map(Number);
    const dt = new Date(now);
    dt.setHours(hh, mm, 0, 0);
    if (dt > now) {
      next = { name: p, time: t, dt };
      break;
    }
  }
  if (!next) {
    document.getElementById("next-name").textContent = "Ertangi Bomdod";
    document.getElementById("next-time").textContent = times.Bomdod || "—";
    document.getElementById("countdown").textContent = "Ertaga";
    return;
  }
  document.getElementById("next-name").textContent = next.name;
  document.getElementById("next-time").textContent = next.time;
}

function startCountdown(times) {
  if (state.countdownTimer) clearInterval(state.countdownTimer);
  function tick() {
    const now = new Date();
    let next = null;
    for (const p of FARZ_NAMES) {
      const t = times[p];
      if (!t) continue;
      const [hh, mm] = t.split(":").map(Number);
      const dt = new Date(now);
      dt.setHours(hh, mm, 0, 0);
      if (dt > now) { next = { name: p, dt }; break; }
    }
    if (!next) {
      document.getElementById("countdown").textContent = "Ertangi vaqtlar uchun";
      return;
    }
    const ms = next.dt - now;
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    let text = "⏳ ";
    if (h > 0) text += `${h}s ${m}d`;
    else if (m > 0) text += `${m}d ${s}son`;
    else text += `${s}son`;
    text += " qoldi";
    document.getElementById("countdown").textContent = text;
  }
  tick();
  state.countdownTimer = setInterval(tick, 1000);
}

function renderQibla(q) {
  document.getElementById("qibla-bearing").textContent = `${q.bearing.toFixed(1)}°`;
  document.getElementById("qibla-distance").textContent =
    `${q.distance_km.toLocaleString("uz-UZ", { maximumFractionDigits: 0 })} km`;
  // Arrow rotation (SVG already pointing up — adjust by bearing)
  document.getElementById("qibla-arrow").setAttribute(
    "transform", `rotate(${q.bearing})`
  );
}

// ============== Utils ==============
function showLoading(v) {
  document.getElementById("loading").classList.toggle("hidden", !v);
}

function showError(msg) {
  document.getElementById("loading").classList.add("hidden");
  document.getElementById("app").classList.add("hidden");
  document.getElementById("error").classList.remove("hidden");
  document.getElementById("error-msg").textContent = msg;
}

function buildUrl(path) {
  const url = new URL(path, location.origin);
  if (tg?.initData) {
    url.searchParams.set("initData", tg.initData);
  } else if (tg?.initDataUnsafe?.user?.id) {
    // dev fallback
    url.searchParams.set("tg_id", tg.initDataUnsafe.user.id);
  }
  return url.toString();
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function toISODate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ============== Boot ==============
document.addEventListener("DOMContentLoaded", init);
