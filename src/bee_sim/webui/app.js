import { WSClient } from "/ws_client.js";
const canvas = document.getElementById("view"), ctx = canvas.getContext("2d");
const playpauseBtn = document.getElementById("playpause");
const speedSlider = document.getElementById("speed"), speedLabel = document.getElementById("speedLabel");
const beesCount = document.getElementById("beesCount"), simTime = document.getElementById("simTime"), pausedSpan = document.getElementById("paused");
document.querySelectorAll("button[data-add]").forEach(btn=>btn.addEventListener("click",()=>{ const count = parseInt(btn.getAttribute("data-add"),10); ws.add(count); }));
speedSlider.addEventListener("input",()=>{ const v = parseFloat(speedSlider.value); speedLabel.textContent = v.toFixed(1) + "x"; ws.speed(v); });
playpauseBtn.addEventListener("click", ()=> ws.toggle() );
const ws = new WSClient(); ws.connect();
let lastView=null; ws.onView((view)=>{ lastView=view; beesCount.textContent=view.bees.length; simTime.textContent=view.t.toFixed(2);
  pausedSpan.textContent = view.paused ? "true" : "false"; playpauseBtn.textContent = view.paused ? "Play" : "Pause";
  speedLabel.textContent = view.speed.toFixed(1) + "x"; if (canvas.width!==view.width || canvas.height!==view.height){ canvas.width=view.width; canvas.height=view.height; } });
function draw(v){ ctx.clearRect(0,0,canvas.width,canvas.height); ctx.fillStyle="#0f1115"; ctx.fillRect(0,0,canvas.width,canvas.height);
  if(!v) return; for(const b of v.bees){ ctx.beginPath(); ctx.arc(b.x,b.y,4,0,Math.PI*2); ctx.fillStyle="#ffd54a"; ctx.fill();
    const dx=Math.cos(b.heading)*6, dy=Math.sin(b.heading)*6; ctx.beginPath(); ctx.moveTo(b.x,b.y); ctx.lineTo(b.x+dx,b.y+dy); ctx.strokeStyle="#fff2b3"; ctx.lineWidth=1; ctx.stroke(); } }
(function loop(){ requestAnimationFrame(loop); draw(lastView); })();
