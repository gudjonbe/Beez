from __future__ import annotations
from typing import Any, Iterable
import random, math, inspect

from bee_sim.domain.colony.hive import Hive
from bee_sim.domain.environment.flowers import FlowerField
from bee_sim.domain.communication.signals import Signal, SignalBus
from bee_sim.domain.environment.weather import Weather

class World:
    """Simulation world: hive, signals, flowers, deposits, environment."""
    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width; self.height = height; self.rng = rng

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
            return F.get(flower_id)
        # Common storage patterns
        store = getattr(F, "flowers", None)
        if isinstance(store, dict):
            return store.get(flower_id)
        if isinstance(store, (list, tuple)):
            for f in store:
                if getattr(f, "id", None) == flower_id:
                    return f
        return None

    def deposit(self, nectar: float) -> None:
        if nectar > 0:
            self.total_deposited += float(nectar)

    def add_flowers(self, n: int) -> None:
        self.flowers.add_random(n)

    def add_flower_at(self, x: float, y: float, n: int = 1) -> None:
        self.flowers.add_at(x, y, n=n)

    # hive helpers
    def hive_entrance(self) -> tuple[float, float]:
        return self._hive.entrance_xy

    # --- world step ---
    def step(self, dt: float) -> None:
        if dt <= 0.0: return

        # Weather first (affects flow/regeneration and foraging open)
        self.weather.step(dt)
        regen_scale = self.weather.nectar_index

        # environment (flowers) — try passing regeneration scaling if supported
        # Try common signatures: step(dt, regen_scale=...), step(dt, scale), step(dt, factor)
        stepped = False
        try:
            self.flowers.step(dt, regen_scale=regen_scale); stepped = True
        except TypeError:
            try:
                self.flowers.step(dt, regen_scale); stepped = True
            except TypeError:
                try:
                    self.flowers.step(dt, scale=regen_scale); stepped = True
                except TypeError:
                    try:
                        self.flowers.step(dt, factor=regen_scale); stepped = True
                    except TypeError:
                        pass
        if not stepped:
            # Fallback to original API
            self.flowers.step(dt)

        # signals
        self.signals.step(dt)

        # slow fields: brood pheromone (nurse bias) + forager primer (slows nurse→forager)
        self._brood_acc += dt
        self._primer_acc += dt

        if self._brood_acc >= 1.0:
            self._brood_acc = 0.0
            hx, hy = self.hive
            self.signals.emit(Signal(kind="brood_pheromone", x=hx, y=hy,
                                     radius=self._hive.brood_radius,
                                     intensity=0.5, decay=0.12, ttl=3.0, source_id=0))

        if self._primer_acc >= 2.0:
            self._primer_acc = 0.0
            hx, hy = self.hive
            self.signals.emit(Signal(kind="forager_primer", x=hx, y=hy,
                                     radius=self.hive_radius * 2.0,
                                     intensity=0.25, decay=0.05, ttl=6.0, source_id=0))

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
        return sum(1 for s in self.signals.signals if s.kind == "waggle")

    def _flowers_snapshot_list(self) -> list[dict]:
        """Robust flower snapshot across different FlowerField implementations."""
        F = self.flowers
        # Prefer a ready-made list from snapshot()
        if hasattr(F, "snapshot"):
            try:
                val = F.snapshot()
                if isinstance(val, list):
                    return val
            except Exception:
                pass

        # Next, try common container patterns
        it: Iterable = []
        if hasattr(F, "all"):
            try: it = list(F.all())
            except Exception: it = []
        elif hasattr(F, "to_list"):
            try: it = list(F.to_list())
            except Exception: it = []
        elif hasattr(F, "iter"):
            try: it = list(F.iter())
            except Exception: it = []
        elif hasattr(F, "flowers"):
            store = getattr(F, "flowers")
            if isinstance(store, dict): it = list(store.values())
            elif isinstance(store, (list, tuple)): it = list(store)

        out: list[dict] = []
        for f in it:
            if hasattr(f, "snapshot"):
                try:
                    out.append(f.snapshot()); continue
                except Exception:
                    pass
            out.append({
                "x": float(getattr(f, "x", 0.0)),
                "y": float(getattr(f, "y", 0.0)),
                "frac": float(getattr(f, "frac", 1.0)) if not callable(getattr(f, "frac", None)) else float(getattr(f, "frac")()),
                "id": getattr(f, "id", None)
            })
        return out

    def snapshot(self) -> dict:
        hx, hy = self.hive
        ex, ey = self.hive_entrance()
        wsnap = self.weather.snapshot()
        return {
            "hive": {"x": hx, "y": hy, "r": self.hive_radius},
            "hive_brood_r": self._hive.brood_radius,
            "hive_entrance": {"x": ex, "y": ey},
            "flowers_remaining": self.flowers.remaining(),
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

