from __future__ import annotations
import asyncio, json, time
from typing import Dict, Any
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute, Mount
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect
from pathlib import Path

from bee_sim.api import SimController

# Serve UI from bee_sim/webui
UI_DIR = Path(__file__).resolve().parents[1] / "webui"

SIM_TICK_HZ = 60
_sim = SimController()
_loop_task: asyncio.Task | None = None

async def sim_loop():
    tick = 1.0 / SIM_TICK_HZ
    last = time.perf_counter()
    while True:
        now = time.perf_counter(); dt = now - last; last = now
        _sim.step(dt)
        await asyncio.sleep(max(0.0, tick - (time.perf_counter() - now)))

class ClientSession:
    def __init__(self, ws: WebSocket):
        self.ws = ws; self.send_task: asyncio.Task | None = None; self.hz = 30

    async def run(self):
        await self.ws.accept()
        self.send_task = asyncio.create_task(self.sender())
        try:
            while True:
                data = json.loads(await self.ws.receive_text())
                await self.handle(data)
        except WebSocketDisconnect:
            pass
        finally:
            if self.send_task: self.send_task.cancel()

    async def sender(self):
        while True:
            await asyncio.sleep(1.0 / max(1, self.hz))
            try:
                await self.ws.send_text(json.dumps({"type": "view", "payload": _sim.get_view()}))
            except Exception:
                break

    async def handle(self, data: Dict[str, Any]):
        t = data.get("type")
        if t == "subscribe":
            hz = int(data.get("hz", 30)); self.hz = max(1, min(120, hz))
            await self.ws.send_text(json.dumps({"type": "ack", "payload": {"subscribe_hz": self.hz}}))
        elif t == "cmd":
            action = data.get("action")
            if action == "toggle":
                paused = _sim.toggle_paused()
                await self.ws.send_text(json.dumps({"type": "ack", "payload": {"paused": paused}}))
            elif action == "play":
                _sim.set_paused(False)
                await self.ws.send_text(json.dumps({"type": "ack", "payload": {"paused": False}}))
            elif action == "pause":
                _sim.set_paused(True)
                await self.ws.send_text(json.dumps({"type": "ack", "payload": {"paused": True}}))
            elif action == "speed":
                value = float(data.get("value", 1.0)); _sim.set_speed(value)
                await self.ws.send_text(json.dumps({"type": "ack", "payload": {"speed": value}}))
            elif action == "add_bees":
                count = int(data.get("count", 1)); _sim.add_bees(count)
                await self.ws.send_text(json.dumps({"type": "ack", "payload": {"added": count}}))
            else:
                await self.ws.send_text(json.dumps({"type": "error", "message": f"Unknown action: {action}"}))
        else:
            await self.ws.send_text(json.dumps({"type": "error", "message": f"Unknown type: {t}"}))

async def homepage(request):
    return FileResponse(UI_DIR / "index.html")

routes = [
    Route("/", endpoint=homepage),
    WebSocketRoute("/ws", endpoint=lambda ws: ClientSession(ws).run()),
    Mount("/", app=StaticFiles(directory=UI_DIR, html=False), name="static"),
]

app = Starlette(routes=routes)

@app.on_event("startup")
async def _on_start():
    global _loop_task
    if _loop_task is None:
        _loop_task = asyncio.create_task(sim_loop())
