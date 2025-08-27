// Make sure we import the same version and see a startup log
import { WSClient } from "./ws_client.js?v=7";
console.log("[ui] app.js loaded v7");

const kindSelect  = document.getElementById("beeKind");
const canvas      = document.getElementById("view");
const ctx         = canvas.getContext("2d");

const playPauseBtn = document.getElementById("playpause");
const speedSlider  = document.getElementById("speed");
const speedLabel   = document.getElementById("speedLabel");

const beesCount = document.getElementById("beesCount");
const simTime   = document.getElementById("simTime");
const pausedEl  = document.getElementById("paused");
const flowersLeftEl = document.getElementById("flowersLeft");
const depositedEl = document.getElementById("deposited");
const roleStatsEl = document.getElementById("roleStats");
const signalStatsEl = document.getElementById("signalStats");

const ws = new WSClient();
ws.connect();

// Add bees
document.querySelectorAll('button[data-add]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const count = parseInt(btn.getAttribute('data-add'), 10);
    const kind  = kindSelect ? kindSelect.value : 'worker';
    ws.add(count, kind);
  });
});

// Add flowers
document.querySelectorAll('button[data-add-flower]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const count = parseInt(btn.getAttribute('data-add-flower'), 10);
    ws.addFlowers(count);
  });
});

// Click canvas to add 1 flower at location
canvas.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (canvas.width / rect.width);
  const y = (e.clientY - rect.top)  * (canvas.height / rect.height);
  ws.addFlowerAt(x, y, 1);
});

// Speed control
speedSlider.addEventListener('input', () => {
  const v = parseFloat(speedSlider.value);
  speedLabel.textContent = `${v.toFixed(1)}x`;
  ws.speed(v);
});

// Play / Pause
playPauseBtn.addEventListener('click', () => ws.toggle());

// ---- incoming view frames ----
let lastView = null;
ws.onView((view) => {
  lastView = view;

  beesCount.textContent = view.bees.length;
  simTime.textContent   = view.t.toFixed(2);

  pausedEl.textContent  = view.paused ? 'true' : 'false';
  playPauseBtn.textContent = view.paused ? 'Play' : 'Pause';

  speedLabel.textContent = `${view.speed.toFixed(1)}x`;

  if (flowersLeftEl && view.world) {
    flowersLeftEl.textContent = view.world.flowers_remaining ?? 0;
  }
  if (depositedEl && view.world) {
    depositedEl.textContent = (view.world.total_deposited ?? 0).toFixed(1);
  }

  if (roleStatsEl && view.stats && view.stats.roles) {
    const roles = view.stats.roles;
    roleStatsEl.innerHTML = Object.keys(roles).sort().map(k => `<div>${k}: <b>${roles[k]}</b></div>`).join("");
  }
  if (signalStatsEl && view.stats && view.stats.signals) {
    const sigs = view.stats.signals;
    signalStatsEl.innerHTML = Object.keys(sigs).sort().map(k => `<div>${k}: <b>${sigs[k]}</b></div>`).join("");
  }

  if (canvas.width !== view.width || canvas.height !== view.height) {
    canvas.width  = view.width;
    canvas.height = view.height;
  }
});

// ---- rendering ----
function draw(v) {
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#0f1115';
  ctx.fillRect(0, 0, w, h);

  if (!v) return;

  // hive
  if (v.world && v.world.hive) {
    const hvc = v.world.hive;
    ctx.beginPath();
    ctx.arc(hvc.x, hvc.y, hvc.r, 0, Math.PI * 2);
    ctx.strokeStyle = '#66b2ff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // flowers
  if (v.world && Array.isArray(v.world.flowers)) {
    ctx.font = '18px system-ui, emoji';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (const f of v.world.flowers) {
      const frac = (typeof f.frac === 'number') ? f.frac : (f.visited ? 0.1 : 1.0);
      const a = 0.25 + 0.75 * Math.max(0, Math.min(1, frac));
      ctx.globalAlpha = a;
      ctx.fillText('🌸', f.x, f.y);
    }
    ctx.globalAlpha = 1.0;
  }

  // ---- bees: workers first, queens last ----
  const workers = v.bees.filter(b => b.kind !== 'queen');
  const queens  = v.bees.filter(b => b.kind === 'queen');

  function drawWorker(b) {
    // flash halo if recently emitted a signal
    if (b.flash && b.flash > 0) {
      const alpha = Math.max(0, Math.min(1, b.flash));
      ctx.beginPath();
      ctx.arc(b.x, b.y, 8, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 220, 90, ${alpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // foragers use the bee emoji; others keep the small circle
    if (b.role === 'forager') {
      ctx.font = '8px system-ui, emoji';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('🐝', b.x, b.y);
    } else {
      ctx.beginPath();
      ctx.arc(b.x, b.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffd54a';
      ctx.fill();
    }

    // heading tick (all non-queen bees)
    const dx = Math.cos(b.heading) * 6;
    const dy = Math.sin(b.heading) * 6;
    ctx.beginPath();
    ctx.moveTo(b.x, b.y);
    ctx.lineTo(b.x + dx, b.y + dy);
    ctx.strokeStyle = '#fff2b3';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // draw workers first
  for (const b of workers) drawWorker(b);

  // draw queens last, on top
  for (const b of queens) {
    if (b.flash && b.flash > 0) {
      const alpha = Math.max(0, Math.min(1, b.flash));
      ctx.beginPath();
      ctx.arc(b.x, b.y, 9, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 220, 90, ${alpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    ctx.font = '10px system-ui, emoji';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('👑', b.x, b.y);
  }
}

// animation loop
(function loop(){ requestAnimationFrame(loop); draw(lastView); })();

