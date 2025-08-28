from __future__ import annotations
import math, random
from .bee import Bee
from bee_sim.domain.communication.signals import Signal

class QueenBee(Bee):
    """Simple queen: stays near hive center, emits mandibular pheromone pulses."""
    def __init__(self, id: int, x: float, y: float):
        # vx, vy start at zero (she moves slowly)
        super().__init__(id, x, y, 0.0, 0.0)
        self.kind = "queen"
        self.role = "queen"
        self._emit_acc = 0.0  # timer for pheromone pulse

    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.3):
        """Small shared helper (queen has one too to avoid earlier AttributeError)."""
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
                # tiny random walk near center
                self._random_walk(dt * 0.25, rng)

            # emit queen mandibular pheromone periodically
            self._emit_acc += dt
            if self._emit_acc >= 1.5:
                self._emit_acc = 0.0
                world.signals.emit(Signal(
                    kind="queen_mandibular", x=hx, y=hy, radius=world.hive_radius * 1.5,
                    intensity=0.6, decay=0.1, ttl=2.0, source_id=self.id
                ))
                self.flash_timer = max(self.flash_timer, 0.4)
        else:
            # fallback if no world
            self._random_walk(dt * 0.25, rng)

        self._clamp(width, height)

