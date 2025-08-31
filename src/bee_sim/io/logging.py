from __future__ import annotations
import csv, json, os, time, asyncio, threading, queue, pathlib, datetime
from typing import Dict, Optional

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None

class RunLogger:
    """Per-frame run logger.
    - Writes rows to runs/<run_id>/frames.csv
    - Optionally streams full frame JSONs to a websocket (e.g. ws://localhost:8000/ws/ingest or /ws/metrics)
    """
    def __init__(self, root: str = "runs", run_id: Optional[str] = None, ws_url: Optional[str] = None, token: Optional[str] = None):
        self.root = pathlib.Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = self.root / self.run_id; self.dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.dir / "frames.csv"
        self.meta_path = self.dir / "meta.json"
        self.ws_url = ws_url; self.token = token
        self._queue: "queue.Queue[dict]" = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._csv_fieldnames: Optional[list[str]] = None
        self.meta_path.write_text(json.dumps({"run_id": self.run_id, "created": time.time(), "ws_url": self.ws_url}, indent=2))

    def start(self) -> None:
        self._stop.clear()
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True); self._writer_thread.start()
        if self.ws_url:
            self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True); self._ws_thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._writer_thread: self._writer_thread.join(timeout=2)
        if self._ws_thread: self._ws_thread.join(timeout=2)

    def log(self, frame: Dict) -> None:
        """Enqueue a frame dict."""
        self._queue.put(frame)

    # ---- internals ---------------------------------------------------------
    def _flatten(self, frame: Dict) -> Dict[str, object]:
        out: Dict[str, object] = {}
        for k, v in frame.items():
            if k == "stats" and isinstance(v, dict):
                for sk, sv in v.items():
                    if isinstance(sv, dict):
                        for sk2, sv2 in sv.items():
                            out[f"stats.{sk}.{sk2}"] = sv2
                    else:
                        out[f"stats.{sk}"] = sv
            elif isinstance(v, (int, float, str, bool)):
                out[k] = v
        return out

    def _writer_loop(self) -> None:
        f = None; writer = None
        try:
            while not self._stop.is_set() or not self._queue.empty():
                try:
                    frame = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                flat = self._flatten(frame)
                if self._csv_fieldnames is None:
                    self._csv_fieldnames = sorted(flat.keys())
                    f = open(self.csv_path, "w", newline="", encoding="utf-8")
                    writer = csv.DictWriter(f, fieldnames=self._csv_fieldnames)
                    writer.writeheader()
                if any(k not in self._csv_fieldnames for k in flat.keys()):
                    self._csv_fieldnames = sorted(set(self._csv_fieldnames) | set(flat.keys()))
                    try:
                        import pandas as pd  # optional
                        df = pd.read_csv(self.csv_path)
                        for missing in [k for k in self._csv_fieldnames if k not in df.columns]:
                            df[missing] = None
                        df = df[self._csv_fieldnames]
                        df.to_csv(self.csv_path, index=False)
                        f = open(self.csv_path, "a", newline="", encoding="utf-8")
                        writer = csv.DictWriter(f, fieldnames=self._csv_fieldnames)
                    except Exception:
                        pass
                if writer is None:
                    f = open(self.csv_path, "a", newline="", encoding="utf-8")
                    writer = csv.DictWriter(f, fieldnames=self._csv_fieldnames)
                row = {k: flat.get(k, None) for k in self._csv_fieldnames}
                writer.writerow(row)
                if f: f.flush()
        finally:
            if f: f.close()

    def _ws_loop(self) -> None:
        if websockets is None:
            return
        async def run() -> None:
            url = self.ws_url
            if not url: return
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}run_id={self.run_id}"
            if self.token: url += f"&token={self.token}"
            backoff = 0.5
            while not self._stop.is_set():
                try:
                    async with websockets.connect(url, max_queue=32) as ws:
                        backoff = 0.5
                        while not self._stop.is_set():
                            try:
                                frame = self._queue.get(timeout=0.1)
                            except queue.Empty:
                                await asyncio.sleep(0.05); continue
                            await ws.send(json.dumps(frame))
                except Exception:
                    await asyncio.sleep(backoff); backoff = min(5.0, backoff * 1.7)
        asyncio.run(run())
