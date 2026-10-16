/**
 * WaterAI Analysis - monitoring.js
 * PH-W218 jonli monitoring: qiymat kartalari, real vaqt grafiklari va dataset yig'ish boshqaruvi.
 */

const MON_KEYS = ["ph", "tds", "ec", "salinity", "orp", "temperature"];
const MON_DECIMALS = { ph: 2, temperature: 1 };

// Me'yor chegaralari (grafikda kesik chiziq) va holat tekshiruvi
const MON_NORMS = {
  ph: { lines: [6.5, 8.5], ok: (v) => v >= 6.5 && v <= 8.5, text: "6.5 – 8.5" },
  tds: { lines: [1000], ok: (v) => v <= 1000, text: "≤ 1000" },
  ec: { lines: [1000], ok: (v) => v <= 1000, text: "≤ 1000" },
  salinity: { lines: [1000], ok: (v) => v <= 1000, text: "≤ 1000" },
  orp: { lines: [200, 600], ok: (v) => v >= 200 && v <= 600, text: "200 – 600 (tavsiya)" },
  temperature: { lines: [], ok: (v) => v >= 5 && v <= 30, text: "5 – 30" },
};

const SERIES_COLOR = "#078be5";
const GRID_COLOR = "rgba(148, 163, 184, 0.18)";
const NORM_COLOR = "#94a3b8";

const series = [];        // [{timestamp, ph, tds, ...}]
const charts = {};
let rangeSec = 600;
let lastTimestamp = null;
let historyLoaded = false;

/* ---------------------------------------------------------------- Grafiklar */

// Me'yor chiziqlari: faqat joriy shkala oralig'iga tushsa chiziladi (shkalani buzmaydi)
const normLinesPlugin = {
  id: "normLines",
  afterDatasetsDraw(chart) {
    const lines = chart.options.plugins.normLines?.lines || [];
    const { ctx, chartArea, scales } = chart;
    lines.forEach((y) => {
      if (y < scales.y.min || y > scales.y.max) return;
      const py = scales.y.getPixelForValue(y);
      ctx.save();
      ctx.strokeStyle = NORM_COLOR;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(chartArea.left, py);
      ctx.lineTo(chartArea.right, py);
      ctx.stroke();
      ctx.restore();
    });
  },
};

// Kursor ostidagi vertikal chiziq (crosshair)
const crosshairPlugin = {
  id: "crosshair",
  afterDraw(chart) {
    const active = chart.tooltip?.getActiveElements?.() || [];
    if (!active.length) return;
    const x = active[0].element.x;
    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.strokeStyle = "rgba(100, 116, 139, 0.45)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};

function initCharts() {
  MON_KEYS.forEach((key) => {
    const canvas = document.getElementById(`chart_${key}`);
    if (!canvas) return;
    charts[key] = new Chart(canvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [{
          data: [],
          borderColor: SERIES_COLOR,
          backgroundColor: "rgba(7, 139, 229, 0.08)",
          fill: true,
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHitRadius: 10,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          normLines: { lines: MON_NORMS[key].lines },
          tooltip: {
            displayColors: false,
            callbacks: {
              label: (item) => `${Device.fmt(item.parsed.y, MON_DECIMALS[key] || 0)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { maxTicksLimit: 5, maxRotation: 0, color: "#94a3b8", font: { size: 10 } },
          },
          y: {
            grace: "10%",
            grid: { color: GRID_COLOR },
            border: { display: false },
            ticks: { maxTicksLimit: 5, color: "#94a3b8", font: { size: 10 } },
          },
        },
      },
      plugins: [normLinesPlugin, crosshairPlugin],
    });
  });
}

function visibleSeries() {
  if (!rangeSec || !series.length) return series;
  const last = new Date(series[series.length - 1].timestamp).getTime();
  return series.filter((p) => last - new Date(p.timestamp).getTime() <= rangeSec * 1000);
}

function renderCharts() {
  const data = visibleSeries();
  const labels = data.map((p) => new Date(p.timestamp).toLocaleTimeString());
  MON_KEYS.forEach((key) => {
    const chart = charts[key];
    if (!chart) return;
    const values = data.map((p) => p[key]);
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update("none");

    const dec = MON_DECIMALS[key] || 0;
    const minEl = document.getElementById(`chart_${key}_min`);
    const maxEl = document.getElementById(`chart_${key}_max`);
    if (values.length) {
      minEl.innerText = Device.fmt(Math.min(...values), dec);
      maxEl.innerText = Device.fmt(Math.max(...values), dec);
    } else {
      minEl.innerText = maxEl.innerText = "--";
    }
  });
}

function setRange(sec) {
  rangeSec = sec;
  document.querySelectorAll(".range-btn").forEach((btn) => {
    const active = Number(btn.dataset.range) === sec;
    btn.classList.toggle("bg-[#078be5]", active);
    btn.classList.toggle("text-white", active);
    btn.classList.toggle("text-slate-500", !active);
  });
  renderCharts();
}

async function loadHistory() {
  historyLoaded = true;
  const { ok, data } = await Device.request("/api/device/history");
  if (!ok || !Array.isArray(data)) return;
  series.length = 0;
  data.forEach((p) => series.push(p));
  lastTimestamp = series.length ? series[series.length - 1].timestamp : null;
  renderCharts();
}

/* ---------------------------------------------------------- Joriy qiymatlar */

function renderTiles(s) {
  const v = s.values;
  MON_KEYS.forEach((key) => {
    const val = v[key].value;
    document.getElementById(`tile_${key}`).innerText = Device.fmt(val, MON_DECIMALS[key] || 0);
    const ok = MON_NORMS[key].ok(val);
    const dot = document.getElementById(`tile_${key}_badge`);
    const state = document.getElementById(`tile_${key}_state`);
    dot.className = `w-2 h-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`;
    state.className = `mt-1 text-[11px] font-semibold ${ok ? "text-emerald-600" : "text-rose-600"}`;
    state.innerText = `${ok ? "✓ Normal" : "⚠ Me’yordan tashqari"} · ${MON_NORMS[key].text}`;
  });
  document.getElementById("tile_sg").innerText = Device.fmt(v.sg.value);
  document.getElementById("tile_cf").innerText = Device.fmt(v.cf.value);
  document.getElementById("tile_humidity").innerText = Device.fmt(v.humidity.value);
  document.getElementById("monReadingWarn").classList.toggle("hidden", !!s.reading_valid);
}

/* ---------------------------------------------------------- Dataset yig'ish */

const STATUS_TEXT = {
  valid: '<span class="text-emerald-600 font-bold">🟢 Yaroqli</span>',
  conditional: '<span class="text-amber-600 font-bold">🟡 Shartli</span>',
  invalid: '<span class="text-rose-600 font-bold">🔴 Yaroqsiz</span>',
};

function renderRecorder(r) {
  document.getElementById("statTotal").innerText = r.total_rows;
  document.getElementById("statSession").innerText = r.session_rows;
  document.getElementById("statSkipped").innerText = r.skipped;
  document.getElementById("statLast").innerText = r.last_row
    ? new Date(r.last_row.timestamp).toLocaleTimeString()
    : "—";

  document.getElementById("recBadge").classList.toggle("hidden", !r.recording);
  document.getElementById("recStartBtn").classList.toggle("hidden", r.recording);
  document.getElementById("recStopBtn").classList.toggle("hidden", !r.recording);
  document.querySelectorAll("#recForm input, #recForm select").forEach((el) => { el.disabled = r.recording; });

  const tbody = document.getElementById("recentRows");
  if (!r.recent.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="py-4 px-3 text-center text-slate-400">Hozircha yozuv yo‘q</td></tr>';
    return;
  }
  const esc = Device.escapeHtml;
  tbody.innerHTML = r.recent.map((row) => `
    <tr class="hover:bg-sky-50/30">
      <td class="py-2 px-3 font-mono">${new Date(row.timestamp).toLocaleTimeString()}</td>
      <td class="py-2 px-3 font-mono">${Device.fmt(row.ph, 2)}</td>
      <td class="py-2 px-3 font-mono">${Device.fmt(row.tds)}</td>
      <td class="py-2 px-3 font-mono">${Device.fmt(row.ec)}</td>
      <td class="py-2 px-3 font-mono">${Device.fmt(row.salinity)}</td>
      <td class="py-2 px-3 font-mono">${Device.fmt(row.orp)}</td>
      <td class="py-2 px-3 font-mono">${Device.fmt(row.temperature, 1)}</td>
      <td class="py-2 px-3">${esc(row.label || "—")}</td>
      <td class="py-2 px-3">${STATUS_TEXT[row.quality_status] || esc(row.quality_status)}</td>
      <td class="py-2 px-3 text-slate-400">${esc(row.trigger)}</td>
    </tr>`).join("");
}

async function startRecording(e) {
  e.preventDefault();
  const body = {
    sample_name: document.getElementById("rec_sample_name").value,
    source_type: document.getElementById("rec_source_type").value,
    location: document.getElementById("rec_location").value,
    label: document.getElementById("rec_label").value,
    heartbeat_sec: Number(document.getElementById("rec_heartbeat").value),
  };
  const { ok, data } = await Device.request("/api/device/recording/start", { method: "POST", body: JSON.stringify(body) });
  Device.showMessage(data.message || (ok ? "Boshlandi" : "Xato"), ok ? "success" : "error");
  Device.refresh();
}

async function stopRecording() {
  const { data } = await Device.request("/api/device/recording/stop", { method: "POST" });
  Device.showMessage(data.message || "To‘xtatildi", "info");
  Device.refresh();
}

async function clearDataset() {
  if (!confirm("Butun PH-W218 dataseti o‘chiriladi. Davom etasizmi?")) return;
  const { ok, data } = await Device.request("/api/device/dataset/clear", { method: "POST" });
  Device.showMessage(data.message || "Xato", ok ? "info" : "error");
  Device.refresh();
}

/* ------------------------------------------------------------------ Holat */

Device.onStatus((s) => {
  const live = s && (s.state === "online" || s.state === "reconnecting") && s.values;
  const hasData = live || series.length > 0;
  document.getElementById("monOffline").classList.toggle("hidden", !!hasData);
  document.getElementById("monLive").classList.toggle("hidden", !hasData);

  if (s && s.recorder) renderRecorder(s.recorder);
  if (!live) return;

  renderTiles(s);
  if (!historyLoaded) {
    loadHistory();
    return;
  }
  if (s.last_update && s.last_update !== lastTimestamp) {
    lastTimestamp = s.last_update;
    const point = { timestamp: s.last_update };
    MON_KEYS.forEach((k) => { point[k] = s.values[k].value; });
    series.push(point);
    if (series.length > 1800) series.shift();
    renderCharts();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  setRange(rangeSec);
  document.querySelectorAll(".range-btn").forEach((btn) => {
    btn.addEventListener("click", () => setRange(Number(btn.dataset.range)));
  });
  document.getElementById("recForm").addEventListener("submit", startRecording);
  document.getElementById("recStopBtn").addEventListener("click", stopRecording);
  const clearBtn = document.getElementById("clearBtn");
  if (clearBtn) clearBtn.addEventListener("click", clearDataset);
  document.getElementById("downloadBtn").addEventListener("click", (e) => {
    const r = Device.status()?.recorder;
    if (r && r.total_rows === 0) {
      e.preventDefault();
      Device.showMessage("Dataset hali bo‘sh — avval yig‘ishni boshlang.", "warning");
    }
  });
});
