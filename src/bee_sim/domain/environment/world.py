from __future__ import annotations
from typing import Any
import random

from bee_sim.domain.colony.hive import Hive
from bee_sim.domain.environment.flowers import FlowerField
from bee_sim.domain.communication.signals import Signal, SignalBus

class World:
    """Simulation world: hive, signals, flowers, deposits, environment."""
    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width; self.height = height; self.rng = rng

        # Hive geometry (keep legacy attributes for compatibility)
        hx, hy = width * 0.5, height * 0.55
        hr = min(width, height) * 0.12
        self.hive = (hx, hy)           # kept for existing code
        self.hive_radius = hr          # kept for existing code
        self._hive = Hive(hx, hy, hr)  # new richer hive model

        # Signals & environment
        self.signals = SignalBus()
        self.flowers = FlowerField(width, height, rng)
        self.total_deposited: float = 0.0

        # Field emitters accumulators
        self._primer_acc = 0.0
        self._brood_acc = 0.0

    # --- external API kept stable ---
    def get_flower(self, flower_id: int):
        return self.flowers.get(flower_id)

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

        # environment
        self.flowers.step(dt)
        self.signals.step(dt)

        # slow field emissions (brood pheromone, forager primer)
        self._brood_acc += dt
        self._primer_acc += dt

        if self._brood_acc >= 1.0:
            self._brood_acc = 0.0
            hx, hy = self.hive
            self.signals.emit(Signal(kind="brood_pheromone", x=hx, y=hy, radius=self._hive.brood_radius,
                                     intensity=0.5, decay=0.12, ttl=3.0, source_id=0))

        if self._primer_acc >= 2.0:
            self._primer_acc = 0.0
            hx, hy = self.hive
            # light global primer centered at hive; very slow decay, long ttl
            self.signals.emit(Signal(kind="forager_primer", x=hx, y=hy, radius=self.hive_radius * 2.0,
                                     intensity=0.25, decay=0.05, ttl=6.0, source_id=0))

    # --- receivers drain helper called by receiver bees ---
    def service_receiver(self, dt: float, rate_per_bee: float = 1.2) -> None:
        drained = self._hive.drain(dt, rate_per_bee)
        if drained > 0.0:
            self.deposit(drained)

    # --- stats & snapshot ---
    def waggle_active(self) -> int:
        # Count active waggle signals as a proxy for recruitment intensity
        return sum(1 for s in self.signals.signals if s.kind == "waggle")

    def snapshot(self) -> dict:
        hx, hy = self.hive

        # --- build a flower list robustly across different FlowerField APIs ---
        flowers_list = []
        F = self.flowers

        try:
            if hasattr(F, "all"):
                # iterable of Flower objects
                flowers_list = [ (f.snapshot() if hasattr(f, "snapshot")
                                  else {"x": getattr(f, "x", 0.0),
                                        "y": getattr(f, "y", 0.0),
                                        "frac": getattr(f, "frac", 1.0),
                                        "id": getattr(f, "id", None)}) 
                                 for f in F.all() ]
            elif hasattr(F, "snapshot"):
                # some implementations return a ready-to-serve list[dict]
                val = F.snapshot()
                if isinstance(val, list):
                    flowers_list = val
                else:
                    # if it returns a dict or something else, fall back below
                    pass
            elif hasattr(F, "to_list"):
                flowers_list = [ (f.snapshot() if hasattr(f, "snapshot")
                                  else {"x": getattr(f, "x", 0.0),
                                        "y": getattr(f, "y", 0.0),
                                        "frac": getattr(f, "frac", 1.0),
                                        "id": getattr(f, "id", None)})
                                 for f in F.to_list() ]
            elif hasattr(F, "iter"):
                flowers_list = [ (f.snapshot() if hasattr(f, "snapshot")
                                  else {"x": getattr(f, "x", 0.0),
                                        "y": getattr(f, "y", 0.0),
                                        "frac": getattr(f, "frac", 1.0),
                                        "id": getattr(f, "id", None)})
                                 for f in F.iter() ]
            elif hasattr(F, "flowers"):
                # common internal: dict of id->Flower or list of Flower
                store = getattr(F, "flowers")
                if isinstance(store, dict):
                    it = store.values()
                elif isinstance(store, (list, tuple)):
                    it = store
                else:
                    it = []
                flowers_list = [ (f.snapshot() if hasattr(f, "snapshot")
                                  else {"x": getattr(f, "x", 0.0),
                                        "y": getattr(f, "y", 0.0),
                                        "frac": getattr(f, "frac", 1.0),
                                        "id": getattr(f, "id", None)})
                                 for f in it ]
        except Exception:
            # last resort: show nothing rather than crashing
            flowers_list = []

        return {
            "hive": {"x": hx, "y": hy, "r": self.hive_radius},
            "flowers_remaining": self.flowers.remaining(),
            "total_deposited": self.total_deposited,
            "hive_queue": self._hive.receiver_queue,
            "flowers": flowers_list,
        }

