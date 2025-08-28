from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import random, math

from collections import Counter
from bee_sim.domain.agents.worker import WorkerBee, set_receiver_rate, set_tremble_threshold
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
    role: str = "unknown"
    flash_kind: str | None = None  # NEW: helps color halos

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
        # Seed workers
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

    # --- runtime controls ---------------------------------------------------
    def set_paused(self, paused: bool) -> None: self._paused = paused
    def toggle_paused(self) -> bool: self._paused = not self._paused; return self._paused
    def set_speed(self, speed: float) -> None: self._speed = max(0.0, min(4.0, float(speed)))

    def set_receiver_rate(self, v: float) -> None: set_receiver_rate(v)
    def set_tremble_threshold(self, v: float) -> None: set_tremble_threshold(v)

    def add_bees(self, n: int, kind: str = "worker") -> None:
        if kind == "queen":
            qx, qy = self.world.hive
            self._bees.append(QueenBee(self._next_id, qx, qy)); self._next_id += 1
        else:
            for _ in range(n):
                self._bees.append(self._new_worker())

    # --- step & stats -------------------------------------------------------
    def step(self, dt: float) -> None:
        if self._paused or dt <= 0.0: return
        dt *= self._speed; self._t += dt
        self.world.step(dt)
        for b in self._bees:
            b.step(dt, self.width, self.height, self.rng, world=self.world)

    def _role_counts(self) -> Dict[str,int]:
        c = Counter()
        for b in self._bees:
            c[getattr(b, "role", "unknown")] += 1
        return dict(c)

    def _signal_counts(self) -> Dict[str,int]:
        bus = getattr(self.world, "signals", None)
        c = Counter()
        if bus is not None:
            for s in bus.signals:
                c[s.kind] += 1
        return dict(c)

    def _receivers_active(self) -> int:
        hx, hy = self.world.hive
        r = self.world.hive_radius * 0.6
        r2 = r * r
        n = 0
        for b in self._bees:
            if getattr(b, "role", None) == "receiver":
                dx = b.x - hx; dy = b.y - hy
                if dx*dx + dy*dy <= r2:
                    n += 1
        return n

    def get_view(self) -> dict:
        bees_view = [BeeView(**b.snapshot()) for b in self._bees]
        stats = {
            "roles": self._role_counts(),
            "signals": self._signal_counts(),
            "receiver_queue": getattr(self.world, "_hive").receiver_queue,
            "queue_avg": getattr(self.world, "_queue_ema", 0.0),
            "waggle_active": self.world.waggle_active(),
            "receivers_active": self._receivers_active(),
            "recruiting_foragers": self.world.waggle_active(),  # proxy
        }
        return {
            "t": self._t, "paused": self._paused, "speed": self._speed,
            "width": self.width, "height": self.height,
            "bees": [bv.__dict__ for bv in bees_view],
            "world": self.world.snapshot(),
            "stats": stats,
        }

