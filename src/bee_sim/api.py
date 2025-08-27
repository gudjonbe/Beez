from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import random, math
from collections import Counter

from bee_sim.domain.agents.worker import WorkerBee
from bee_sim.domain.agents.queen import QueenBee
from bee_sim.domain.environment.world import World

@dataclass
class BeeView:
    id: int
    x: float
    y: float
    heading: float
    kind: str
    flash: float

class SimController:
    def __init__(self, width: int = 960, height: int = 540, seed: int | None = None):
        self.width = width; self.height = height
        self.rng = random.Random(seed)
        self._t = 0.0; self._next_id = 1; self._paused = False; self._speed = 1.0
        self.world = World(width, height, self.rng)

        # Agents
        self._bees: list = []
        # One queen by default
        qx, qy = self.world.hive
        self._bees.append(QueenBee(self._next_id, qx, qy)); self._next_id += 1
        # Seed some workers
        for _ in range(5):
            self._bees.append(self._new_worker())

    def _new_worker(self) -> WorkerBee:
        x = self.rng.uniform(0, self.width)
        y = self.rng.uniform(0, self.height)
        angle = self.rng.uniform(0, 6.283)
        speed = self.rng.uniform(40, 80)
        vx = speed * math.cos(angle); vy = speed * math.sin(angle)
        w = WorkerBee(self._next_id, x, y, vx, vy); self._next_id += 1
        return w

    def set_paused(self, paused: bool) -> None: self._paused = paused
    def toggle_paused(self) -> bool: self._paused = not self._paused; return self._paused
    def set_speed(self, speed: float) -> None: self._speed = max(0.0, min(4.0, float(speed)))

    def add_bees(self, n: int, kind: str = "worker") -> None:
        if kind == "queen":
            qx, qy = self.world.hive
            self._bees.append(QueenBee(self._next_id, qx, qy)); self._next_id += 1
        else:
            for _ in range(n):
                self._bees.append(self._new_worker())

    def step(self, dt: float) -> None:
        if self._paused or dt <= 0.0: return
        dt *= self._speed; self._t += dt
        self.world.step(dt)
        for b in self._bees:
            b.step(dt, self.width, self.height, self.rng, world=self.world)

    def _role_counts(self) -> Dict[str,int]:
        c = Counter()
        for b in self._bees:
            role = getattr(b, "role", "unknown")
            c[role] += 1
        return dict(c)

    def _signal_counts(self) -> Dict[str,int]:
        bus = getattr(self.world, "signals", None)
        c = Counter()
        if bus is not None:
            for s in bus.signals:
                c[s.kind] += 1
        return dict(c)

    def get_view(self) -> dict:
        bees_view = [b.snapshot() for b in self._bees]  # no dataclass construction
        stats = {"roles": self._role_counts(), "signals": self._signal_counts()}
        return {
            "t": self._t, "paused": self._paused, "speed": self._speed,
            "width": self.width, "height": self.height,
            "bees": bees_view,
            "world": self.world.snapshot(),
            "stats": stats,
        }

