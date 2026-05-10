// ═══════════════════════════════════════════════════════════════
// TAQVIMbot Mini App v2 — vanilla JS
// Animated progress ring · 3D tilt · live countdown · qibla compass
// ═══════════════════════════════════════════════════════════════

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
const RING_R = 88;
const RING_CIRC = 2 * Math.PI * RING_R; // ≈ 553

const state = {
  user: null,
  subscriptions: [],
  currentRegion: null,
  currentTimes: null,
  currentDate: new Date(),
  countdownTimer: null,
  ringPrevWindow: null,
};

// ═══════════ Init ═══════════
async function init() {
  if (tg) {
    tg.ready();
    tg.expand();
    tg.disableVerticalSwipes?.();
    tg.MainButton.hide();
  }

  setup3DTilt();

  try {
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

// ═══════════ 3D Tilt ═══════════
function setup3DTilt() {
  document.querySelectorAll("[data-tilt]").forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      const tiltX = (y - 0.5) * 8;
      const tiltY = (x - 0.5) * -8;
      card.style.transform =
        `perspective(1200px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-2px)`;
    });
    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
    card.addEventListener("touchstart", () => {
      card.style.transition = "transform 0.3s var(--ease)";
    });
  });
}

// ═══════════ Date nav ═══════════
function setupDateNav() {
  document.getElementById("btn-prev-day").onclick = () => {
    state.currentDate = new Date(state.currentDate.getTime() - 86400000);
    loadTimesForDate(state.currentDate);
    hapticImpact();
  };
  document.getElementById("btn-next-day").onclick = () => {
    state.currentDate = new Date(state.currentDate.getTime() + 86400000);
    loadTimesForDate(state.currentDate);
    hapticImpact();
  };
  document.getElementById("btn-today").onclick = () => {
    state.currentDate = new Date();
    loadTimesForDate(state.currentDate);
    hapticImpact();
  };
}

function hapticImpact() {
  try { tg?.HapticFeedback?.impactOccurred?.("light"); } catch (_) {}
}

// ═══════════ Load times ═══════════
async function loadTimesForDate(d) {
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

// ═══════════ Render ═══════════
function renderTimes(data) {
  document.getElementById("city-name").textContent = data.region.name.toUpperCase();

  // Sanalar
  const d = new Date(data.date);
  const months = ["yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentyabr","oktyabr","noyabr","dekabr"];
  const weekdays = ["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba","Yakshanba"];
  const wd = weekdays[(d.getDay() + 6) % 7];
  const dStr = `${d.getDate()}-${months[d.getMonth()]}, ${d.getFullYear()} · ${wd}`;
  document.getElementById("date-greg").textContent = dStr;
  document.getElementById("date-hijri").textContent = data.hijri;

  // Prayer list
  const list = document.getElementById("prayer-list");
  list.innerHTML = "";
  const now = new Date();
  const isToday = data.date === toISODate(now);

  // Determine upcoming farz (for "upcoming" highlight)
  let upcomingFarz = null;
  if (isToday) {
    for (const p of FARZ_NAMES) {
      const t = data.times[p];
      if (!t) continue;
      const [hh, mm] = t.split(":").map(Number);
      const dt = new Date(now); dt.setHours(hh, mm, 0, 0);
      if (dt > now) { upcomingFarz = p; break; }
    }
  }

  ["Bomdod", "Quyosh", "Peshin", "Asr", "Shom", "Xufton"].forEach((p) => {
    const t = data.times[p] || "—";
    const row = document.createElement("div");
    row.className = "prayer-row";

    if (isToday && t !== "—") {
      const [hh, mm] = t.split(":").map(Number);
      const dt = new Date(now); dt.setHours(hh, mm, 0, 0);
      if (dt < now) row.classList.add("passed");
    }
    if (p === upcomingFarz) row.classList.add("upcoming");

    row.innerHTML = `
      <span class="icon">${PRAYER_ICONS[p] || "🕌"}</span>
      <span class="name">${p}</span>
      <span class="time">${t}</span>
    `;
    list.appendChild(row);
  });

  // Hero — next farz + ring + countdown
  if (isToday) {
    startCountdown(data.times);
  } else {
    setHero("—", "--:--", "Boshqa kun", "🕌", 0);
    if (state.countdownTimer) clearInterval(state.countdownTimer);
  }

  // Ayah
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

function setHero(name, time, countdown, emoji, progress) {
  document.getElementById("next-name").textContent = name;
  document.getElementById("next-time").textContent = time;
  document.getElementById("countdown").innerHTML = countdown ? `⏳ ${countdown}` : "";
  document.getElementById("hero-emoji").textContent = emoji;
  // Progress: 0..1, ring goes from EMPTY to FULL as time approaches
  const offset = RING_CIRC * (1 - progress);
  document.getElementById("ring-progress").style.strokeDashoffset = offset;
}

function startCountdown(times) {
  if (state.countdownTimer) clearInterval(state.countdownTimer);
  state.ringPrevWindow = null;

  function tick() {
    const now = new Date();
    let next = null;
    let prev = null;

    // Find next upcoming farz + the previous farz that just passed
    const farzInOrder = [];
    for (const p of FARZ_NAMES) {
      const t = times[p];
      if (!t) continue;
      const [hh, mm] = t.split(":").map(Number);
      const dt = new Date(now); dt.setHours(hh, mm, 0, 0);
      farzInOrder.push({ name: p, dt, time: t });
    }
    for (const item of farzInOrder) {
      if (item.dt > now) { next = item; break; }
      prev = item;
    }
    if (!next) {
      // All passed — next is tomorrow's Bomdod
      const b = times.Bomdod;
      if (b) {
        const [hh, mm] = b.split(":").map(Number);
        const dt = new Date(now); dt.setHours(hh, mm, 0, 0);
        dt.setDate(dt.getDate() + 1);
        next = { name: "Bomdod (ertangi)", dt, time: b };
      }
    }

    if (!next) {
      setHero("—", "--:--", "Ma'lumot yo'q", "🕌", 0);
      return;
    }

    // Progress: from prev → next (or fallback: from now-1h → next)
    const windowStart = prev ? prev.dt.getTime() : (next.dt.getTime() - 3600 * 1000);
    const windowEnd = next.dt.getTime();
    const elapsed = now.getTime() - windowStart;
    const total = windowEnd - windowStart;
    const progress = Math.max(0, Math.min(1, elapsed / total));

    const ms = next.dt - now;
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    let cd = "";
    if (h > 0) cd = `${h} soat ${m} daqiqa`;
    else if (m > 0) cd = `${m} daqiqa ${s} soniya`;
    else cd = `${s} soniya`;
    cd += " qoldi";

    const cleanName = next.name.replace(" (ertangi)", "");
    const emoji = PRAYER_ICONS[cleanName] || "🕌";

    setHero(next.name, next.time, cd, emoji, progress);
  }

  tick();
  state.countdownTimer = setInterval(tick, 1000);
}

function renderQibla(q) {
  document.getElementById("qibla-bearing").textContent = `${q.bearing.toFixed(1)}°`;
  document.getElementById("qibla-distance").textContent =
    `${q.distance_km.toLocaleString("uz-UZ", { maximumFractionDigits: 0 })} km`;
  document.getElementById("qibla-arrow").setAttribute(
    "transform", `rotate(${q.bearing})`
  );
}

// ═══════════ Utils ═══════════
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

document.addEventListener("DOMContentLoaded", init);
