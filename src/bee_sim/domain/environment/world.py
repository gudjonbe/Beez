from __future__ import annotations
from typing import Dict, Any
import random

from .flowers import FlowerField
from bee_sim.domain.communication.bus import SignalBus
from bee_sim.domain.communication.signals import Signal

class World:
    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width
        self.height = height
        self.rng = rng

        self.hive = (width * 0.5, height * 0.5)
        self.hive_radius = 30.0

        self.flowers = FlowerField(width, height, rng)
        self.signals = SignalBus(width, height)

        self.total_deposited = 0.0
        self._bg_acc = 0.0

    def step(self, dt: float):
        self.flowers.step(dt)
        self.signals.step(dt)

        self._bg_acc += dt
        if self._bg_acc >= 1.0:
            self._bg_acc = 0.0
            hx, hy = self.hive
            # Queen mandibular pheromone
            self.signals.emit(Signal(kind="queen_mandibular", x=hx, y=hy, radius=self.hive_radius*1.5,
                                     intensity=1.0, decay=0.15, ttl=6.0, source_id=0))
            # Brood pheromone
            self.signals.emit(Signal(kind="brood", x=hx, y=hy, radius=self.hive_radius*1.2,
                                     intensity=0.8, decay=0.20, ttl=5.0, source_id=0))

    def add_flowers(self, n: int):
        self.flowers.add_random(n)

    def add_flower_at(self, x: float, y: float, n: int = 1):
        self.flowers.add_at(x, y, n=n)

    def get_flower(self, flower_id: int):
        return self.flowers.get(flower_id)

    def deposit(self, amount: float):
        self.total_deposited += amount

    def snapshot(self) -> Dict[str, Any]:
        hx, hy = self.hive
        sigs = self.signals.snapshot(include_kinds={"waggle"}, max_items=24)
        return {
            "hive": {"x": hx, "y": hy, "r": self.hive_radius},
            "flowers": self.flowers.snapshot(),
            "flowers_remaining": self.flowers.remaining(),
            "total_deposited": self.total_deposited,
            "signals": sigs,
        }
