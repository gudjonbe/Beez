from __future__ import annotations
import math, random
from .bee import Bee
from bee_sim.domain.communication.signals import Signal

class QueenBee(Bee):
    """Simple queen: stays near hive center, emits mandibular pheromone pulses."""
    def __init__(self, id: int, x: float, y: float):
        super().__init__(id, x, y, 0.0, 0.0)
        self.kind = "queen"
        self.role = "queen"
        self._emit_acc = 0.0
        self.last_signal_kind = None

    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.3):
        dx, dy = (x - self.x), (y - self.y)
        angle = math.atan2(dy, dx)
        speed = 45.0 * speed_scale
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def step(self, dt: float, width: int, height: int, rng: random.Random, world=None):
        if world is not None:
            hx, hy = world.hive
            dist = math.hypot(hx - self.x, hy - self.y)
            if dist > (world.hive_radius * 0.3):
                self._go_towards(hx, hy, dt, speed_scale=0.6)
            else:
                self._random_walk(dt * 0.25, rng)

            # emit queen mandibular pheromone periodically
            self._emit_acc += dt
            if self._emit_acc >= 1.5:
                self._emit_acc = 0.0
                world.signals.emit(Signal(
                    kind="queen_mandibular", x=hx, y=hy, radius=world.hive_radius * 1.5,
                    intensity=0.6, decay=0.1, ttl=2.0, source_id=self.id
                ))
                self.last_signal_kind = "queen_mandibular"
                self.flash_timer = max(self.flash_timer, 0.4)
        else:
            self._random_walk(dt * 0.25, rng)

        self._clamp(width, height)

    def snapshot(self) -> dict:
        heading = math.atan2(self.vy, self.vx)
        return {
            "id": self.id, "x": self.x, "y": self.y,
            "heading": heading, "kind": self.kind,
            "flash": self.flash_timer, "role": "queen",
            "flash_kind": self.last_signal_kind,
        }

