import { WSClient } from "./ws_client.js";

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

const ws = new WSClient();
ws.connect();

document.querySelectorAll('button[data-add]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const count = parseInt(btn.getAttribute('data-add'), 10);
    const kind  = kindSelect ? kindSelect.value : 'worker';
    ws.add(count, kind);
  });
});

speedSlider.addEventListener('input', () => {
  const v = parseFloat(speedSlider.value);
  speedLabel.textContent = `${v.toFixed(1)}x`;
  ws.speed(v);
});

playPauseBtn.addEventListener('click', () => ws.toggle());

let lastView = null;

ws.onView((view) => {
  lastView = view;
  beesCount.textContent = view.bees.length;
  simTime.textContent   = view.t.toFixed(2);
  pausedEl.textContent  = view.paused ? 'true' : 'false';
  playPauseBtn.textContent = view.paused ? 'Play' : 'Pause';
  speedLabel.textContent = `${view.speed.toFixed(1)}x`;
  if (flowersLeftEl && view.world) flowersLeftEl.textContent = view.world.flowers_remaining ?? 0;
  if (canvas.width !== view.width || canvas.height !== view.height) {
    canvas.width  = view.width; canvas.height = view.height;
  }
});

function draw(v) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#0f1115'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!v) return;

  // Hive
  if (v.world && v.world.hive) {
    const h = v.world.hive;
    ctx.beginPath(); ctx.arc(h.x, h.y, h.r, 0, Math.PI * 2);
    ctx.strokeStyle = '#66b2ff'; ctx.lineWidth = 2; ctx.stroke();
  }

  // Flowers as emojis
  if (v.world && Array.isArray(v.world.flowers)) {
    ctx.font = '18px system-ui, emoji';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (const f of v.world.flowers) {
      ctx.globalAlpha = f.visited ? 0.35 : 1.0;
      ctx.fillText('🌸', f.x, f.y);
    }
    ctx.globalAlpha = 1.0;
  }

  // Bees
  for (const b of v.bees) {
    ctx.beginPath(); ctx.arc(b.x, b.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#ffd54a'; ctx.fill();
    const dx = Math.cos(b.heading) * 6, dy = Math.sin(b.heading) * 6;
    ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x + dx, b.y + dy);
    ctx.strokeStyle = '#fff2b3'; ctx.lineWidth = 1; ctx.stroke();
  }
}

(function loop(){ requestAnimationFrame(loop); draw(lastView); })();

