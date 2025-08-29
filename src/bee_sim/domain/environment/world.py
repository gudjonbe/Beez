from __future__ import annotations
from typing import Any, Iterable, List
import random, math

from bee_sim.domain.colony.hive import Hive
from bee_sim.domain.environment.flowers import FlowerField
from bee_sim.domain.communication.signals import Signal, SignalBus
from bee_sim.domain.environment.weather import Weather

class World:
    """Simulation world: hive, signals, flowers, deposits, environment."""
    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width
        self.height = height
        self.rng = rng

        # Hive geometry (keep legacy tuple/float for compatibility)
        hx, hy = width * 0.5, height * 0.55
        hr = min(width, height) * 0.12
        self.hive = (hx, hy)           # used in many places
        self.hive_radius = hr          # used in many places
        self._hive = Hive(hx, hy, hr)  # richer hive model

        # Signals & environment
        self.signals = SignalBus()
        self.flowers = FlowerField(width, height, rng)
        self.total_deposited: float = 0.0

        # Weather (Phase C.1)
        self.weather = Weather(rng)

        # Slow field emitters (Phase B)
        self._primer_acc = 0.0
        self._brood_acc = 0.0

        # Queue EMA for UI stats
        self._queue_ema = 0.0
        self._queue_tau = 2.0  # seconds

    # --- external API kept stable ---
    def get_flower(self, flower_id: int):
        """Robust accessor that tolerates different FlowerField backends."""
        F = self.flowers
        # Preferred
        if hasattr(F, "get"):
            try:
                return F.get(flower_id)
            except Exception:
                pass
        # Common storage patterns
        store = getattr(F, "flowers", None)
        if isinstance(store, dict):
            return store.get(flower_id)
        if isinstance(store, (list, tuple)):
            for f in store:
                if getattr(f, "id", None) == flower_id:
                    return f
        # Not found
        return None

    def deposit(self, nectar: float) -> None:
        if nectar > 0:
            self.total_deposited += float(nectar)

    def add_flowers(self, n: int) -> None:
        if hasattr(self.flowers, "add_random"):
            self.flowers.add_random(n)

    def add_flower_at(self, x: float, y: float, n: int = 1) -> None:
        if hasattr(self.flowers, "add_at"):
            self.flowers.add_at(x, y, n=n)

    # hive helpers
    def hive_entrance(self) -> tuple[float, float]:
        return self._hive.entrance_xy

    # --- world step ---
    def step(self, dt: float) -> None:
        if dt <= 0.0:
            return

        # Weather first (affects flow/regeneration and foraging open)
        if hasattr(self.weather, "step"):
            self.weather.step(dt)
        # For now FlowerField.step(dt) does not take scaling; keep it simple.
        try:
            self.flowers.step(dt)
        except TypeError:
            # Some variants accept (dt, *) – best-effort for regen scaling
            try:
                self.flowers.step(dt=dt)
            except Exception:
                pass

        # Update queue EMA
        q = self._hive.receiver_queue
        alpha = 1.0 - math.exp(-max(1e-6, dt) / max(1e-6, self._queue_tau))
        self._queue_ema += (q - self._queue_ema) * alpha

    # --- receivers drain helper called by receiver bees ---
    def service_receiver(self, dt: float, rate_per_bee: float = 1.2) -> None:
        drained = self._hive.drain(dt, rate_per_bee)
        if drained > 0.0:
            self.deposit(drained)

    # --- stats & snapshot ---
    def waggle_active(self) -> int:
        # Count active waggle signals as a proxy for recruitment intensity
        return sum(1 for s in getattr(self.signals, "signals", []) if getattr(s, "kind", "") == "waggle")

    
    def _flowers_snapshot_list(self) -> list[dict]:
        """Robust flower snapshot across different FlowerField implementations."""
        F = self.flowers
    
        # Prefer a ready-made list from snapshot()
        snap = getattr(F, "snapshot", None)
        if callable(snap):
            try:
                val = snap()
                if isinstance(val, list):
                    return val
            except Exception:
                pass
    
        # Fallback: inspect known containers
        it = []
        store = getattr(F, "flowers", None)
        if isinstance(store, dict):
            it = list(store.values())
        elif isinstance(store, (list, tuple)):
            it = list(store)
        else:
            # Last resort: iterate the object if possible
            try:
                it = list(F)  # type: ignore
            except Exception:
                it = []
    
        out: list[dict] = []
        for f in it:
            try:
                fid = getattr(f, "id", None)
                if fid is None:
                    continue
    
                # Coordinates (tolerant)
                x = float(getattr(f, "x", 0.0))
                y = float(getattr(f, "y", 0.0))
    
                # --- frac: call f.frac(); fallback to nectar/cap ---
                try:
                    frac = float(f.frac())
                except Exception:
                    try:
                        nectar = getattr(f, "nectar", getattr(f, "value", None))
                        cap    = getattr(f, "cap", getattr(f, "capacity", None))
                        if nectar is not None and cap not in (None, 0):
                            frac = float(nectar) / float(cap)
                        else:
                            frac = 0.0
                    except Exception:
                        frac = 0.0
    
                # clamp to [0,1]
                if frac < 0.0:
                    frac = 0.0
                elif frac > 1.0:
                    frac = 1.0
    
                # visited: prefer explicit attributes; else infer from low frac
                v = getattr(f, "ever_visited", None)
                if v is None:
                    v = getattr(f, "visited", None)
                if callable(v):
                    try:
                        visited = bool(v())
                    except Exception:
                        visited = (frac < 0.05)
                elif v is not None:
                    visited = bool(v)
                else:
                    visited = (frac < 0.05)
    
                out.append({"id": fid, "x": x, "y": y, "frac": frac, "visited": visited})
            except Exception:
                continue
    
        return out

    
    def snapshot(self) -> dict:
        hx, hy = self.hive
        ex, ey = self.hive_entrance()
        wsnap = self.weather.snapshot()
    
        # Flowers remaining: prefer FlowerField.remaining(); fallback to count of list
        try:
            flowers_remaining = self.flowers.remaining()
        except Exception:
            try:
                flowers_remaining = len(self._flowers_snapshot_list())
            except Exception:
                flowers_remaining = 0
    
        return {
            "hive": {"x": hx, "y": hy, "r": self.hive_radius},
            "hive_brood_r": getattr(self._hive, "brood_radius", self.hive_radius * 0.55),
            "hive_entrance": {"x": ex, "y": ey},
            "flowers_remaining": flowers_remaining,
            "total_deposited": self.total_deposited,
            "hive_queue": self._hive.receiver_queue,
            "queue_avg": self._queue_ema,
            "flowers": self._flowers_snapshot_list(),
            "weather": {
                "tod": wsnap.tod, "nectar": wsnap.nectar,
                "rain": wsnap.rain, "open": wsnap.open,
                "mode": wsnap.mode,
            },
        }
    


