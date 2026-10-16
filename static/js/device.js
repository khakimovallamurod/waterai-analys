/**
 * WaterAI Analysis - device.js
 * PH-W218 qurilmasi bilan ishlash: ulanish/uzish, holatni so'rash va ulanish panelini yangilash.
 */

const Device = (() => {
  const POLL_ACTIVE_MS = 2000;
  const POLL_IDLE_MS = 10000;

  let current = null;
  let timer = null;
  let busy = false;
  const listeners = [];

  const $ = (id) => document.getElementById(id);

  async function request(url, options = {}) {
    try {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        ...options,
      });
      let data = {};
      try { data = await res.json(); } catch (_) { /* bo'sh javob */ }
      return { ok: res.ok, data };
    } catch (e) {
      return { ok: false, data: { message: "Server bilan aloqa yo‘q" } };
    }
  }

  const STATES = {
    disconnected: { text: "Ulanmagan", dot: "bg-slate-300", color: "text-slate-500" },
    connecting: { text: "Ulanmoqda…", dot: "bg-amber-400 animate-pulse", color: "text-amber-600" },
    online: { text: "Ulandi", dot: "bg-emerald-500 animate-pulse", color: "text-emerald-600" },
    reconnecting: { text: "Aloqa uzildi, qayta ulanmoqda…", dot: "bg-amber-400 animate-pulse", color: "text-amber-600" },
  };

  function render(s) {
    const st = STATES[busy ? "connecting" : (s ? s.state : "disconnected")] || STATES.disconnected;
    const dot = $("devDot");
    const text = $("devStateText");
    const meta = $("devMeta");
    const btnOn = $("devConnectBtn");
    const btnOff = $("devDisconnectBtn");
    if (!dot) return;

    dot.className = `w-2.5 h-2.5 rounded-full inline-block ${st.dot}`;
    text.className = `font-bold ${st.color}`;
    text.innerText = st.text;

    const parts = [];
    if (s && s.device && s.device.ip) parts.push(`IP: ${s.device.ip}`);
    if (s && s.last_update && s.state !== "disconnected") {
      parts.push(`yangilandi: ${new Date(s.last_update).toLocaleTimeString()}`);
    }
    meta.innerText = parts.join(" · ");

    const live = s && (s.state === "online" || s.state === "reconnecting");
    btnOn.classList.toggle("hidden", !!live);
    btnOff.classList.toggle("hidden", !live);
    btnOn.disabled = busy;
    btnOn.querySelector("span").innerText = busy ? "Ulanmoqda…" : "Qurilmaga ulanish";
  }

  function showMessage(text, kind = "info") {
    const el = $("devMessage");
    if (!el) return;
    const styles = {
      success: "bg-emerald-50 text-emerald-700 border-emerald-200",
      error: "bg-rose-50 text-rose-700 border-rose-200",
      warning: "bg-amber-50 text-amber-700 border-amber-200",
      info: "bg-sky-50 text-sky-700 border-sky-200",
    };
    el.className = `mt-3 text-xs font-medium rounded-xl px-3 py-2 border ${styles[kind] || styles.info}`;
    el.innerHTML = text;
  }

  function hideMessage() {
    const el = $("devMessage");
    if (el) el.classList.add("hidden");
  }

  function setStatus(s) {
    current = s;
    render(s);
    listeners.forEach((fn) => fn(s));
    schedule();
  }

  function schedule() {
    clearTimeout(timer);
    const active = current && current.state !== "disconnected";
    timer = setTimeout(refresh, active ? POLL_ACTIVE_MS : POLL_IDLE_MS);
  }

  async function refresh() {
    const { ok, data } = await request("/api/device/status");
    if (ok) setStatus(data);
    else schedule();
  }

  async function connect() {
    if (busy) return;
    busy = true;
    render(current);
    hideMessage();
    const { data } = await request("/api/device/connect", { method: "POST" });
    busy = false;
    if (data.ok) {
      showMessage('<i class="fa-solid fa-circle-check mr-1"></i> Qurilmaga ulandi. Tahlil qiymatlari endi PH-W218 dan real vaqtda olinadi.', "success");
      setTimeout(hideMessage, 5000);
    } else {
      showMessage(
        `<i class="fa-solid fa-triangle-exclamation mr-1"></i> Ulanib bo‘lmadi: <b>${escapeHtml(data.message || "noma’lum xato")}</b>. ` +
        "Qurilma yoqilganini va server bilan bir tarmoqda ekanini tekshiring. Hozircha standart qiymatlar ishlatiladi.",
        "error"
      );
    }
    if (data.status) setStatus(data.status);
    else refresh();
  }

  async function disconnect() {
    const { data } = await request("/api/device/disconnect", { method: "POST" });
    showMessage('<i class="fa-solid fa-plug-circle-xmark mr-1"></i> Qurilma uzildi. Standart qiymatlarga qaytildi.', "info");
    setTimeout(hideMessage, 4000);
    if (data.status) setStatus(data.status);
    else refresh();
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmt(value, decimals = 0) {
    if (value === null || value === undefined || isNaN(value)) return "--";
    return Number(value).toFixed(decimals);
  }

  function init() {
    const btnOn = $("devConnectBtn");
    const btnOff = $("devDisconnectBtn");
    if (btnOn) btnOn.addEventListener("click", connect);
    if (btnOff) btnOff.addEventListener("click", disconnect);
    refresh();
  }

  return {
    init,
    refresh,
    request,
    fmt,
    escapeHtml,
    showMessage,
    status: () => current,
    onStatus: (fn) => listeners.push(fn),
  };
})();

document.addEventListener("DOMContentLoaded", Device.init);
