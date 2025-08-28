# src/bee_sim/telemetry/ws_server.py
"""
WebSocket + static file server for the BeeSim web UI.

Responsibilities:
- Serve the UI from src/bee_sim/webui (index.html, app.js, style.css, etc.)
- Run the simulation loop on a steady cadence
- Stream "view" frames to connected clients over WebSocket
- Handle simple commands from the UI: play/pause, speed, add bees, add flowers

This file is intentionally small and readable. Anything simulation-related
lives in bee_sim.api (SimController) and the domain modules.
"""

from __future__ import annotations

# stdlib
import asyncio
import json
import time
import traceback
from pathlib import Path
from typing import Any, Dict

# web framework
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

# sim API
from bee_sim.api import SimController


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Where the web UI (index.html, app.js, style.css) is located.
UI_DIR = Path(__file__).resolve().parents[1] / "webui"

# Simulation loop tick rate (Hz). Higher is smoother but uses more CPU.
SIM_TICK_HZ = 60

# Single SimController instance shared across all client sessions.
_sim = SimController()

# Task handle for the background simulation loop.
_loop_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Simulation loop (background task)
# ---------------------------------------------------------------------------

async def sim_loop() -> None:
    """
    Background task that advances the simulation at ~SIM_TICK_HZ.
    We clamp very large dt spikes (after reload/breakpoints) to keep things stable.
    """
    tick = 1.0 / SIM_TICK_HZ
    last = time.perf_counter()
    print(f"[sim] loop starting @ {SIM_TICK_HZ} Hz")

    while True:
        now = time.perf_counter()
        dt = now - last
        last = now

        # Clamp huge dt spikes (e.g., after code reload or debugger pauses).
        if dt > 0.2:
            dt = 0.2

        try:
            _sim.step(dt)
        except Exception as e:
            # Never let a transient sim error kill the loop.
            print("[sim] step error:", repr(e))
            traceback.print_exc()

        # Try to maintain a steady cadence.
        remain = tick - (time.perf_counter() - now)
        await asyncio.sleep(remain if remain > 0 else 0)


# ---------------------------------------------------------------------------
# WebSocket client session
# ---------------------------------------------------------------------------

class ClientSession:
    """
    One instance per connected WebSocket client.

    - On connect: start a sender task that pushes "view" frames at `self.hz`.
    - On message: handle 'subscribe' (set stream rate) and 'cmd' (control sim).
    """

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.send_task: asyncio.Task | None = None
        self.hz: int = 30  # default outbound view stream rate

    async def run(self) -> None:
        """Accept the socket and start the sender; then read/handle incoming messages."""
        await self.ws.accept()
        print("[ws] connected")
        self.send_task = asyncio.create_task(self._sender())

        try:
            while True:
                raw = await self.ws.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await self._error("bad json")
                    continue
                await self._handle(data)

        except WebSocketDisconnect:
            print("[ws] disconnected")

        except Exception as e:
            print("[ws] receive error:", repr(e))
            traceback.print_exc()

        finally:
            if self.send_task:
                self.send_task.cancel()

    async def _sender(self) -> None:
        """Periodically push the current view to the client."""
        while True:
            await asyncio.sleep(1.0 / max(1, self.hz))
            try:
                view = _sim.get_view()
                await self.ws.send_text(json.dumps({"type": "view", "payload": view}))
            except Exception as e:
                # Most commonly the socket was closed; stop the sender.
                print("[ws] sender stopping:", repr(e))
                break

    async def _handle(self, data: Dict[str, Any]) -> None:
        """Dispatch incoming messages."""
        msg_type = data.get("type")

        # Client subscribes to the "view" stream with a desired Hz.
        if msg_type == "subscribe":
            # We ignore 'stream' for now; there's only "view".
            hz = int(data.get("hz", 30))
            self.hz = max(1, min(120, hz))
            await self.ws.send_text(json.dumps({
                "type": "ack",
                "payload": {"subscribe_hz": self.hz}
            }))
            print(f"[ws] subscribe -> {self.hz} Hz")
            return

        # Commands that control the sim.
        if msg_type != "cmd":
            await self._error(f"Unknown type: {msg_type}")
            return

        action = data.get("action")

        # --- Basic controls -------------------------------------------------
        if action == "toggle":
            paused = _sim.toggle_paused()
            await self._ack({"paused": paused})

        elif action == "play":
            _sim.set_paused(False)
            await self._ack({"paused": False})

        elif action == "pause":
            _sim.set_paused(True)
            await self._ack({"paused": True})

        elif action == "speed":
            try:
                value = float(data.get("value", 1.0))
            except (TypeError, ValueError):
                await self._error("speed requires a numeric 'value'")


                
            else:
                _sim.set_speed(value)
                await self._ack({"speed": value})

        # --- Bee management -------------------------------------------------
        elif action == "add_bees":
            try:
                count = int(data.get("count", 1))
            except (TypeError, ValueError):
                await self._error("add_bees requires an integer 'count'")
            else:
                kind = data.get("kind", "worker")
                _sim.add_bees(count, kind=kind)
                await self._ack({"bees_added": count, "kind": kind})

        # --- Flower management ----------------------------------------------
        elif action == "add_flowers":
            # Adds a small random patch; no coordinates expected.
            try:
                count = int(data.get("count", 10))
            except (TypeError, ValueError):
                await self._error("add_flowers requires an integer 'count'")
            else:
                _sim.world.add_flowers(count)
                await self._ack({"flowers_added": count})

        elif action == "add_flower_at":
            # Add flower(s) near a specific point; coordinates required.
            try:
                x = float(data["x"])
                y = float(data["y"])
                n = int(data.get("n", 1))
            except (KeyError, TypeError, ValueError):
                await self._error("add_flower_at requires numeric 'x' and 'y' (and optional integer 'n')")
            else:
                _sim.world.add_flower_at(x, y, n=n)
                await self._ack({"flowers_added": n, "at": [x, y]})


        elif action == "set_param":
            key = data.get("key")
            try:
                value = float(data.get("value"))
            except (TypeError, ValueError):
                await self._error("set_param requires numeric 'value'")
                return
            if key == "receiver_rate":
                _sim.set_receiver_rate(value)
                await self._ack({"param": key, "value": value})
            elif key == "tremble_threshold":
                _sim.set_tremble_threshold(value)
                await self._ack({"param": key, "value": value})
            else:
                await self._error(f"unknown param: {key}")

        # --- Weather --------------------------------------------------------


        elif action == "weather":
            op = data.get("op")
            if op == "mode":
                mode = str(data.get("value", "auto"))
                _sim.world.weather.set_mode(mode)
                await self._ack({"weather_mode": mode})
            elif op == "flow":
                value = data.get("value", 0.7)
                _sim.world.weather.set_flow(value)
                await self._ack({"weather_flow": value})
            elif op == "rain":
                raining = bool(data.get("value", False))
                _sim.world.weather.set_rain(raining)
                await self._ack({"rain": raining})
            else:
                await self._error("weather op must be one of: mode, flow, rain")


        # --- Unknown --------------------------------------------------------
        else:
            await self._error(f"Unknown action: {action}")

    # -----------------------------------------------------------------------
    # Small helpers
    # -----------------------------------------------------------------------

    async def _ack(self, payload: Dict[str, Any]) -> None:
        """Send a small acknowledgment message."""
        await self.ws.send_text(json.dumps({"type": "ack", "payload": payload}))

    async def _error(self, message: str) -> None:
        """Send an error message."""
        await self.ws.send_text(json.dumps({"type": "error", "message": message}))


# ---------------------------------------------------------------------------
# HTTP routes and ASGI app
#   + dev no-cache so updated JS/CSS are always fetched fresh
# ---------------------------------------------------------------------------

class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that disables browser caching (great for development)."""
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        # Only add headers for successful static responses
        if getattr(resp, "status_code", 200) == 200:
            resp.headers["Cache-Control"] = "no-store, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
        return resp


async def homepage(request):
    """Serve the UI entry point with no-cache headers in development."""
    return FileResponse(
        UI_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


async def ws_endpoint(ws: WebSocket):
    """Create a session for each WebSocket client."""
    session = ClientSession(ws)
    await session.run()


routes = [
    Route("/", endpoint=homepage),
    WebSocketRoute("/ws", endpoint=ws_endpoint),
    # Use our no-cache static server for dev
    Mount("/", app=NoCacheStaticFiles(directory=UI_DIR, html=False), name="static"),
]

app = Starlette(routes=routes)


# ---------------------------------------------------------------------------
# App startup: kick off the background sim loop
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _on_start() -> None:
    """Start the background simulation loop once on app startup."""
    global _loop_task
    if _loop_task is None:
        _loop_task = asyncio.create_task(sim_loop())
        print("[app] sim loop task created")

