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
        self._lay_acc = 0.0
        self.lay_period = 3.0
        self.lay_mean = 4
        self.max_brood_buffer = 500


    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.3):
        dx, dy = (x - self.x), (y - self.y)
        angle = math.atan2(dy, dx)
        speed = 45.0 * speed_scale
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.x += self.vx * dt
        self.y += self.vy * dt

    
    def _do_lay(self, world, rng):
        hive = getattr(world, "_hive", None)
        if hive is None:
            return
        snap = getattr(hive, "brood_snapshot", lambda: {})()
        total_brood = int(snap.get("eggs", 0)) + int(snap.get("larvae", 0)) + int(snap.get("pupae", 0))
        if total_brood > self.max_brood_buffer:
            return
        n = max(1, int(rng.expovariate(1.0 / max(1e-6, self.lay_mean))))
        try:
            hive.add_eggs(n, rng)
        except Exception:
            pass

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
                    intensity=0.2, decay=0.1, ttl=2.0, source_id=self.id
                ))
                self.last_signal_kind = "queen_mandibular"
                self.flash_timer = max(self.flash_timer, 0.4)
        else:
            self._random_walk(dt * 0.25, rng)

        # Lay eggs periodically
        self._lay_acc += dt
        if self._lay_acc >= self.lay_period:
            self._lay_acc = 0.0
            try:
                self._do_lay(world, rng)
            except Exception:
                pass

        self._clamp(width, height)

    def snapshot(self) -> dict:
        heading = math.atan2(self.vy, self.vx)
        return {
            "id": self.id, "x": self.x, "y": self.y,
            "heading": heading, "kind": self.kind,
            "flash": self.flash_timer, "role": "queen",
            "flash_kind": self.last_signal_kind,
        }

