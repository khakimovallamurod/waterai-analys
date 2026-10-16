/**
 * WaterAI Analysis - device_analyze.js
 * "Qurilmadan tahlil" tabi: ulanganda PH-W218 real qiymatlari (faqat o'qish uchun),
 * ulanmaganda qurilma parametrlarining standart qiymatlari (tahrirlash mumkin).
 */

const DEVICE_NORMS = {
  ph: (v) => v >= 6.5 && v <= 8.5,
  tds: (v) => v <= 1000,
  ec: (v) => v <= 1000,
  salinity: (v) => v <= 1000,
  orp: (v) => v >= 200 && v <= 600,
  temperature: (v) => v >= 5 && v <= 30,
};
const ADVISORY = ["orp", "temperature"];
const DEVICE_DECIMALS = { ph: 2, temperature: 1 };

let liveMode = null; // null — hali aniqlanmagan, true — qurilmadan, false — standart

const valueInputs = () => document.querySelectorAll(".device-value");

function keyOf(input) {
  return input.id.replace("dev_", "");
}

function setBadge(key, value) {
  const badge = document.getElementById(`dev_${key}_badge`);
  if (!badge) return;
  const base = "text-[10px] font-semibold px-2 py-0.5 rounded-full border ";
  const check = DEVICE_NORMS[key];
  if (!check) {
    badge.innerText = "Ma’lumot";
    badge.className = base + "bg-slate-100 text-slate-500 border-slate-200";
  } else if (isNaN(value)) {
    badge.innerText = "—";
    badge.className = base + "bg-slate-100 text-slate-500 border-slate-200";
  } else if (check(value)) {
    badge.innerText = "Normal";
    badge.className = base + "bg-emerald-100 text-emerald-700 border-emerald-200";
  } else {
    badge.innerText = ADVISORY.includes(key) ? "Tavsiyadan tashqari" : "Me’yordan tashqari";
    badge.className = base + "bg-rose-100 text-rose-700 border-rose-200";
  }
}

function refreshBadges() {
  valueInputs().forEach((input) => setBadge(keyOf(input), parseFloat(input.value)));
}

function restoreDefaults() {
  valueInputs().forEach((input) => { input.value = input.dataset.default; });
  refreshBadges();
}

function setLiveMode(on, s) {
  if (liveMode === on) return;
  liveMode = on;

  valueInputs().forEach((input) => { input.readOnly = on; });
  document.getElementById("data_source_input").value = on ? "device" : "device_default";
  document.getElementById("resetDefaultsBtn").classList.toggle("hidden", on);
  document.getElementById("submitLabel").innerHTML = on
    ? "📡 &nbsp; Qurilmaning real qiymatlari bilan tahlil qilish"
    : "🔍 &nbsp; Standart qiymatlar bilan tahlil qilish";

  if (!on) {
    restoreDefaults();
    document.getElementById("devReadingWarn").classList.add("hidden");
    const note = document.getElementById("valuesSourceNote");
    note.className = "text-xs font-medium rounded-xl px-3 py-2 border bg-amber-50 text-amber-700 border-amber-200";
    note.innerHTML =
      '<i class="fa-solid fa-circle-exclamation mr-1"></i> Qurilma ulanmagan — qurilma parametrlarining <b>standart qiymatlari</b> ko‘rsatilmoqda. ' +
      'Ularni qo‘lda o‘zgartirishingiz mumkin. Real qiymatlar uchun yuqoridagi <b>“Qurilmaga ulanish”</b> tugmasini bosing.';
  }
}

function applyLiveValues(s) {
  Object.entries(s.values).forEach(([key, item]) => {
    const input = document.getElementById(`dev_${key}`);
    if (input) input.value = Device.fmt(item.value, DEVICE_DECIMALS[key] || 0);
  });
  refreshBadges();

  const note = document.getElementById("valuesSourceNote");
  const time = new Date(s.last_update).toLocaleTimeString();
  if (s.state === "online") {
    note.className = "text-xs font-medium rounded-xl px-3 py-2 border bg-emerald-50 text-emerald-700 border-emerald-200";
    note.innerHTML = `<i class="fa-solid fa-satellite-dish mr-1"></i> Qiymatlar PH-W218 qurilmasidan <b>jonli</b> olinmoqda · oxirgi yangilanish ${time}`;
  } else {
    note.className = "text-xs font-medium rounded-xl px-3 py-2 border bg-amber-50 text-amber-700 border-amber-200";
    note.innerHTML = `<i class="fa-solid fa-rotate mr-1"></i> Qurilma bilan aloqa uzildi, qayta ulanmoqda — oxirgi real qiymatlar (${time}) ko‘rsatilmoqda`;
  }
  document.getElementById("devReadingWarn").classList.toggle("hidden", !!s.reading_valid);
}

Device.onStatus((s) => {
  const live = s && (s.state === "online" || s.state === "reconnecting") && s.values;
  if (live) {
    setLiveMode(true, s);
    applyLiveValues(s);
  } else if (!s || s.state !== "connecting") {
    setLiveMode(false, s);
  }
});

document.addEventListener("DOMContentLoaded", () => {
  refreshBadges();
  valueInputs().forEach((input) => {
    input.addEventListener("input", () => setBadge(keyOf(input), parseFloat(input.value)));
  });
  document.getElementById("resetDefaultsBtn").addEventListener("click", restoreDefaults);
});
