from __future__ import annotations
import math, random
from typing import Any
from .bee import Bee

class QueenBee(Bee):
    """Queen that mostly stays near the hive center and emits queen signals."""
    SPEED_MIN = 10.0
    SPEED_MAX = 25.0
    TURN_NOISE = 0.2

    def __init__(self, id: int, x: float, y: float):
        super().__init__(id, x, y, 0.0, 0.0)
        self.kind = "queen"
        self._emit_acc = 0.0

    def step(self, dt: float, width: int, height: int, rng: random.Random, world: Any | None = None) -> None:
        if world is not None:
            hx, hy = world.hive
            dx, dy = (hx - self.x), (hy - self.y)
            dist = math.hypot(dx, dy)
            if dist > world.hive_radius * 0.3:
                self._go_towards(hx, hy, dt, speed_scale=0.3)
            else:
                self._random_walk(dt*0.3, rng)
        else:
            self._random_walk(dt*0.3, rng)
        self._clamp(width, height)

        # Emit queen signals slowly
        self._emit_acc += dt
        if self._emit_acc >= 1.2 and world is not None:
            self._emit_acc = 0.0
            from bee_sim.domain.communication.signals import Signal
            hx, hy = world.hive
            world.signals.emit(Signal(kind="queen_mandibular", x=hx, y=hy, radius=world.hive_radius*1.5,
                                      intensity=1.0, decay=0.15, ttl=6.0, source_id=self.id))
            if rng.random() < 0.08:
                world.signals.emit(Signal(kind="queen_piping", x=hx, y=hy, radius=world.hive_radius*1.0,
                                          intensity=0.6, decay=0.7, ttl=0.9, source_id=self.id))
                self.flash_timer = max(self.flash_timer, 0.4)
