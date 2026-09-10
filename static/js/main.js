/**
 * WaterAI Analysis - Main JS
 * Custom Cursor, Interactive Water Particles Canvas, Phone Mask & Alert Toast
 */

document.addEventListener("DOMContentLoaded", function () {
  initCustomCursor();
  initWaterParticles();
  initPhoneMasks();
  initAlertDismissal();
});

/**
 * 1. 🖱️ Custom Landing Cursor
 */
function initCustomCursor() {
  const dot = document.getElementById('cursor-dot');
  const outline = document.getElementById('cursor-outline');
  if (!dot || !outline) return;

  // Agar sensorli qurilma bo'lsa kursorni ko'rsatmaslik
  if (window.matchMedia("(pointer: coarse)").matches || window.innerWidth < 768) {
    dot.style.display = "none";
    outline.style.display = "none";
    return;
  }

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let outlineX = mouseX;
  let outlineY = mouseY;

  window.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.left = `${mouseX}px`;
    dot.style.top = `${mouseY}px`;
  });

  // Smooth lagging outline
  function animateOutline() {
    outlineX += (mouseX - outlineX) * 0.18;
    outlineY += (mouseY - outlineY) * 0.18;
    outline.style.left = `${outlineX}px`;
    outline.style.top = `${outlineY}px`;
    requestAnimationFrame(animateOutline);
  }
  requestAnimationFrame(animateOutline);

  // Hover expansion on interactive elements
  const hoverTargets = document.querySelectorAll('a, button, input, select, textarea, .glass-card, .preset-btn');
  hoverTargets.forEach(el => {
    el.addEventListener('mouseenter', () => outline.classList.add('cursor-hover'));
    el.addEventListener('mouseleave', () => outline.classList.remove('cursor-hover'));
  });
}

/**
 * 2. 💧 Realistic Floating Water Bubbles & Liquid Wave Ripples
 * (Tarmoq chiziqlari o'rniga haqiqiy suzuvchi tiniq suv pufakchalari va suv to'lqinlari)
 */
function initWaterParticles() {
  const container = document.getElementById('particles-bg');
  if (!container) return;

  const canvas = document.createElement('canvas');
  canvas.style.position = 'absolute';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.pointerEvents = 'none';
  container.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  // 1. Suzuvchi suv pufakchalari (Floating Bubbles)
  const numBubbles = Math.min(Math.floor(width / 35), 45);
  const bubbles = [];

  for (let i = 0; i < numBubbles; i++) {
    bubbles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 8 + 3, // 3px dan 11px gacha
      speed: Math.random() * 0.7 + 0.35,
      wobbleSpeed: Math.random() * 0.02 + 0.01,
      phase: Math.random() * Math.PI * 2,
      opacity: Math.random() * 0.3 + 0.15
    });
  }

  // 2. Interaktiv suv to'lqinlari (Liquid Wave Ripples)
  const ripples = [];

  function addRipple(x, y, maxR = 65) {
    if (ripples.length > 25) ripples.shift();
    ripples.push({
      x: x,
      y: y,
      radius: 2,
      maxRadius: maxR,
      opacity: 0.6,
      speed: 1.8
    });
  }

  let lastRippleTime = 0;
  window.addEventListener('mousemove', (e) => {
    const now = Date.now();
    if (now - lastRippleTime > 120) {
      addRipple(e.clientX, e.clientY, 55);
      lastRippleTime = now;
    }
  });

  window.addEventListener('click', (e) => {
    addRipple(e.clientX, e.clientY, 90);
    setTimeout(() => addRipple(e.clientX, e.clientY, 120), 100);
  });

  let time = 0;

  function render() {
    ctx.clearRect(0, 0, width, height);
    time += 0.02;

    // A) Suv to'lqinlari (Liquid Ripples) chizish
    for (let i = ripples.length - 1; i >= 0; i--) {
      const r = ripples[i];
      r.radius += r.speed;
      r.opacity *= 0.96;

      if (r.radius > r.maxRadius || r.opacity < 0.02) {
        ripples.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.beginPath();
      ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(7, 139, 229, ${r.opacity * 0.55})`;
      ctx.lineWidth = 1.5;
      ctx.shadowColor = 'rgba(7, 139, 229, 0.4)';
      ctx.shadowBlur = 6;
      ctx.stroke();

      // Ichki ikkinchi nozik halqa
      if (r.radius > 10) {
        ctx.beginPath();
        ctx.arc(r.x, r.y, r.radius * 0.65, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(7, 139, 229, ${r.opacity * 0.25})`;
        ctx.lineWidth = 0.9;
        ctx.stroke();
      }
      ctx.restore();
    }

    // B) Suzuvchi suv pufakchalari (Floating Bubbles)
    for (let i = 0; i < bubbles.length; i++) {
      const b = bubbles[i];

      // Yuqoriga ko'tarilish va mayin silkinish
      b.y -= b.speed;
      b.x += Math.sin(time + b.phase) * 0.45;

      if (b.y + b.radius < 0) {
        b.y = height + b.radius + 10;
        b.x = Math.random() * width;
      }

      // Pufakcha tanasi (translucent water bubble)
      ctx.save();
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
      
      const grad = ctx.createRadialGradient(
        b.x - b.radius * 0.3,
        b.y - b.radius * 0.3,
        b.radius * 0.1,
        b.x,
        b.y,
        b.radius
      );
      grad.addColorStop(0, `rgba(255, 255, 255, ${b.opacity * 0.8})`);
      grad.addColorStop(0.6, `rgba(7, 139, 229, ${b.opacity * 0.4})`);
      grad.addColorStop(1, `rgba(5, 116, 193, ${b.opacity * 0.6})`);

      ctx.fillStyle = grad;
      ctx.fill();

      // Pufakcha cheti
      ctx.strokeStyle = `rgba(7, 139, 229, ${b.opacity * 0.5})`;
      ctx.lineWidth = 0.8;
      ctx.stroke();

      // Pufakchaning yaltirashi (specular highlight glint)
      ctx.beginPath();
      ctx.arc(
        b.x - b.radius * 0.35,
        b.y - b.radius * 0.35,
        Math.max(b.radius * 0.25, 1),
        0,
        Math.PI * 2
      );
      ctx.fillStyle = `rgba(255, 255, 255, ${b.opacity * 0.9})`;
      ctx.fill();

      ctx.restore();
    }

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}

/**
 * 3. 📱 O'zbekiston telefon raqami formati: +998 (XX) XXX-XX-XX
 */
function initPhoneMasks() {
  const phoneInputs = document.querySelectorAll(".phone-mask-input, input[name='phone']");

  phoneInputs.forEach(input => {
    if (!input.value || input.value.trim() === "") {
      input.value = "+998 ";
    }

    input.addEventListener("focus", function () {
      if (!this.value || this.value.trim() === "") {
        this.value = "+998 ";
      }
    });

    input.addEventListener("input", function () {
      let raw = this.value.replace(/\D/g, "");

      if (!raw.startsWith("998")) {
        if (raw.startsWith("9")) {
          raw = "998" + raw.slice(1);
        } else {
          raw = "998" + raw;
        }
      }

      raw = raw.substring(0, 12);

      let formatted = "+998";
      if (raw.length > 3) {
        formatted += " (" + raw.substring(3, 5);
      }
      if (raw.length >= 5) {
        formatted += ") " + raw.substring(5, 8);
      }
      if (raw.length >= 8) {
        formatted += "-" + raw.substring(8, 10);
      }
      if (raw.length >= 10) {
        formatted += "-" + raw.substring(10, 12);
      }

      this.value = formatted;
    });

    input.addEventListener("keydown", function (e) {
      if ((e.key === "Backspace" || e.key === "Delete") && this.value.length <= 6) {
        e.preventDefault();
      }
    });
  });
}

/**
 * 4. Alert Toast Dismissal
 */
function initAlertDismissal() {
  const alerts = document.querySelectorAll(".alert-toast");
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-10px)";
      setTimeout(() => alert.remove(), 300);
    }, 5000);
  });
}
