/**
 * WaterAI Analysis - analyze.js
 * Interaktiv sliderlar, namunalar (presets) va real vaqtda yangilash
 */

const PRESETS = {
  vodoprovod: {
    source_type: "Vodoprovod suvi",
    sample_name: "Toshkent shahri vodoprovod suvi",
    temperature: 19.5,
    ph: 7.20,
    tds: 240,
    turbidity: 1.1,
    ec: 310,
    hardness: 150,
    sulfate: 95,
    chloramines: 1.80,
    organic: 1.8,
    trihalomethanes: 12.0
  },
  buloq: {
    source_type: "Artezian suvi",
    sample_name: "Chorvoq tog' buloq suvi",
    temperature: 12.0,
    ph: 7.55,
    tds: 110,
    turbidity: 0.4,
    ec: 140,
    hardness: 80,
    sulfate: 30,
    chloramines: 0.10,
    organic: 0.5,
    trihalomethanes: 1.5
  },
  quduq: {
    source_type: "Quduq suvi",
    sample_name: "Farg'ona vodiysi yerosti quduq suvi",
    temperature: 16.5,
    ph: 7.85,
    tds: 780,
    turbidity: 3.2,
    ec: 890,
    hardness: 260,
    sulfate: 210,
    chloramines: 0.20,
    organic: 3.5,
    trihalomethanes: 8.5
  },
  daryo: {
    source_type: "Daryo suvi",
    sample_name: "Zarafshon daryosi namunalari",
    temperature: 22.0,
    ph: 8.20,
    tds: 850,
    turbidity: 7.5,
    ec: 920,
    hardness: 240,
    sulfate: 280,
    chloramines: 0.40,
    organic: 6.2,
    trihalomethanes: 25.0
  }
};

function updateParam(id, value, decimals = 0) {
  const num = parseFloat(value);
  const formatted = decimals > 0 ? num.toFixed(decimals) : Math.round(num);

  // Qiymat ko'rsatkichini yangilash
  const displayEl = document.getElementById(id + "_val");
  if (displayEl) displayEl.innerText = formatted;

  // Agar slider va number input alohida bo'lsa ularni sinxronlash
  const sliderEl = document.getElementById(id + "_slider");
  if (sliderEl && sliderEl.value != value) sliderEl.value = value;

  const inputEl = document.getElementById(id + "_input");
  if (inputEl && inputEl.value != value) inputEl.value = value;

  // Real vaqt me'yor statusini tekshirish
  checkParamNorm(id, num);
}

function checkParamNorm(id, val) {
  let isBad = false;
  if (id === 'ph' && (val < 6.5 || val > 8.5)) isBad = true;
  if (id === 'tds' && val > 1000) isBad = true;
  if (id === 'turbidity' && val > 5) isBad = true;
  if (id === 'hardness' && val > 200) isBad = true;
  if (id === 'sulfate' && val > 250) isBad = true;
  if (id === 'chloramines' && val > 4) isBad = true;
  if (id === 'organic' && val > 10) isBad = true;
  if (id === 'trihalomethanes' && val > 80) isBad = true;

  const badge = document.getElementById(id + "_badge");
  if (badge) {
    if (isBad) {
      badge.innerText = "Me’yordan yuqori";
      badge.className = "text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 border border-rose-200 transition-colors";
    } else {
      badge.innerText = "Normal";
      badge.className = "text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 transition-colors";
    }
  }
}

function applyPreset(presetKey) {
  const data = PRESETS[presetKey];
  if (!data) return;

  const sampleNameInput = document.getElementById("sample_name");
  if (sampleNameInput && data.sample_name) sampleNameInput.value = data.sample_name;

  const sourceSelect = document.getElementById("source_type");
  if (sourceSelect && data.source_type) sourceSelect.value = data.source_type;

  // Barcha parametrlarni yangilash
  updateParam('temperature', data.temperature, 1);
  updateParam('ph', data.ph, 2);
  updateParam('tds', data.tds, 0);
  updateParam('turbidity', data.turbidity, 1);
  updateParam('ec', data.ec, 0);
  updateParam('hardness', data.hardness, 0);
  updateParam('sulfate', data.sulfate, 0);
  updateParam('chloramines', data.chloramines, 2);
  updateParam('organic', data.organic, 1);
  updateParam('trihalomethanes', data.trihalomethanes, 1);

  // Preset tugmalarining faol holatini belgilash
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.classList.remove('ring-2', 'ring-sky-500', 'bg-sky-50');
  });
  const activeBtn = document.getElementById('preset_' + presetKey);
  if (activeBtn) {
    activeBtn.classList.add('ring-2', 'ring-sky-500', 'bg-sky-50');
  }
}

document.addEventListener("DOMContentLoaded", function () {
  // Boshlang'ich qiymatlarni tekshirish
  const initialParams = [
    { id: 'temperature', dec: 1 },
    { id: 'ph', dec: 2 },
    { id: 'tds', dec: 0 },
    { id: 'turbidity', dec: 1 },
    { id: 'ec', dec: 0 },
    { id: 'hardness', dec: 0 },
    { id: 'sulfate', dec: 0 },
    { id: 'chloramines', dec: 2 },
    { id: 'organic', dec: 1 },
    { id: 'trihalomethanes', dec: 1 }
  ];

  initialParams.forEach(p => {
    const input = document.getElementById(p.id + "_slider");
    if (input) {
      updateParam(p.id, input.value, p.dec);
    }
  });
});
