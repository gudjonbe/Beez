# Beez Metrics Patch — 2025-08-31

This patch makes the **Metrics** page plot *measured values vs. simulation time* reliably, even when the app is hosted under a subpath (e.g. `/beez`). It also adds reconnection logic and compatibility with both `/ws/metrics` **and** `/ws` message formats.

## Files in this patch
- `src/bee_sim/webui/metrics.html` — drop-in replacement with:
  - base-path aware WebSocket URLs
  - automatic fallback to `/ws` if `/ws/metrics` is unavailable
  - support for both raw frames and `{ type:'view', payload: ... }` frames
  - auto-reconnect, light HUD (FPS/trace count), and simple include/exclude regex filters
  - x-axis labeled **Sim time (s)**

## How to apply
1. **Back up** your current `src/bee_sim/webui/metrics.html` (if you’ve customized it).
2. Copy the file from this zip into your repo at the same path:  
   `src/bee_sim/webui/metrics.html`
3. Start your server, e.g.:  
   `uvicorn bee_sim.main:app --reload --port 8000`
4. Open `http://localhost:8000/metrics` (or your deployed URL).  
   The status badge should show **live**, and lines should appear with **x = Sim time (s)**.

### Notes
- If you serve the UI under a base path (e.g. `https://host/beez/metrics`), the WebSocket will connect to `wss://host/beez/ws/metrics` automatically.
- If the explicit `/ws/metrics` endpoint is missing, the page falls back to `/ws` and subscribes to the `view` stream (if your server supports that).
- If `Plotly` is not already bundled by your app, the page will dynamically load it from a CDN.

## Optional server side (FYI)
Your routes should include both the page and the WebSockets (already present in many setups):

```python
from starlette.routing import Route, Mount, WebSocketRoute

routes = [
    Route("/metrics", endpoint=metrics_page),
    WebSocketRoute("/ws", endpoint=ws_endpoint),
    WebSocketRoute("/ws/metrics", endpoint=ws_metrics_endpoint),
]
```

`/ws/metrics` should stream frames shaped like the object returned by `_sim.get_view()` at ~20 Hz.

## Troubleshooting
- If the status shows **closed** or **error**:
  - Open DevTools → **Network** → **WS** to confirm the URL includes your base path.
  - Ensure the server exposes either `/ws/metrics` (raw frames) or `/ws` (wrapped frames).
- If lines are flat or frozen:
  - Make sure the simulation isn't paused in the canvas tab.
