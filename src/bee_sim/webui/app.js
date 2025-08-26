// main.js
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

// --- WS client ---
const ws = new WSClient();
ws.connect();

// Add bees (now includes kind)
document.querySelectorAll('button[data-add]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const count = parseInt(btn.getAttribute('data-add'), 10);
    const kind  = kindSelect ? kindSelect.value : 'worker';
    ws.add(count, kind);
  });
});

// Speed control
speedSlider.addEventListener('input', () => {
  const v = parseFloat(speedSlider.value);
  speedLabel.textContent = `${v.toFixed(1)}x`;
  ws.speed(v);
});

// Play / Pause toggle
playPauseBtn.addEventListener('click', () => ws.toggle());

// --- State updates from server ---
let lastView = null;

ws.onView((view) => {
  lastView = view;

  beesCount.textContent = view.bees.length;
  simTime.textContent   = view.t.toFixed(2);

  pausedEl.textContent  = view.paused ? 'true' : 'false';
  playPauseBtn.textContent = view.paused ? 'Play' : 'Pause';

  speedLabel.textContent = `${view.speed.toFixed(1)}x`;

  if (canvas.width !== view.width || canvas.height !== view.height) {
    canvas.width  = view.width;
    canvas.height = view.height;
  }
});

// --- Rendering ---
function draw(v) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#0f1115';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!v) return;

  for (const b of v.bees) {
    // Bee body
    ctx.beginPath();
    ctx.arc(b.x, b.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#ffd54a';
    ctx.fill();

    // Heading indicator
    const dx = Math.cos(b.heading) * 6;
    const dy = Math.sin(b.heading) * 6;

    ctx.beginPath();
    ctx.moveTo(b.x, b.y);
    ctx.lineTo(b.x + dx, b.y + dy);
    ctx.strokeStyle = '#fff2b3';
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

// Animation loop
(function loop() {
  requestAnimationFrame(loop);
  draw(lastView);
})();

