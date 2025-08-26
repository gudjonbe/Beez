from __future__ import annotations
from typing import Optional, Any, Deque
from collections import deque
import math
from .bee import Bee

class WorkerBee(Bee):
    SPEED_MIN = 40.0
    SPEED_MAX = 120.0
    TURN_NOISE = 0.35
    RESPAWN_SPEED = 60.0

    VISIT_QUANTA = 0.8
    AVOID_MEMORY = 16

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float):
        super().__init__(id, x, y, vx, vy)
        self.state: str = "wander"
        self.target_flower_id: Optional[int] = None
        self.carry: float = 0.0
        self.capacity: float = 3.0
        self._avoid: Deque[int] = deque(maxlen=self.AVOID_MEMORY)

    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.6):
        dx, dy = (x - self.x), (y - self.y)
        angle = math.atan2(dy, dx)
        speed = (self.SPEED_MIN + self.SPEED_MAX) * speed_scale
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def step(self, dt: float, width: int, height: int, rng, world: Any | None = None) -> None:
        if world is None:
            return super().step(dt, width, height, rng)

        if self.state == "wander":
            if self.carry + 1e-6 < self.capacity and world.flowers.remaining() > 0:
                f = world.flowers.reserve_nearest(self.x, self.y, set(self._avoid))
                if f:
                    self.target_flower_id = f.id
                    self.state = "to_flower"
            super().step(dt, width, height, rng)

        elif self.state == "to_flower":
            f = world.get_flower(self.target_flower_id) if self.target_flower_id else None
            if not f or not f.available:
                if self.target_flower_id is not None:
                    world.flowers.release_reservation(self.target_flower_id)
                self.target_flower_id = None
                self.state = "wander"
                return
            dist = math.hypot(f.x - self.x, f.y - self.y)
            if dist < 10.0:
                got = world.flowers.collect_from(f.id, amount=min(self.VISIT_QUANTA, self.capacity - self.carry))
                self.carry += got
                if got > 0.0: self._avoid.append(f.id)
                if (self.carry + 1e-6) < self.capacity and world.flowers.remaining() > 0:
                    nf = world.flowers.reserve_nearest(self.x, self.y, set(self._avoid))
                    if nf:
                        self.target_flower_id = nf.id
                        self.state = "to_flower"
                        return
                self.target_flower_id = None
                self.state = "to_hive"
            else:
                self._go_towards(f.x, f.y, dt)

        elif self.state == "to_hive":
            hx, hy = world.hive
            dist = math.hypot(hx - self.x, hy - self.y)
            if dist < (world.hive_radius + 10.0):
                world.deposit(self.carry); self.carry = 0.0
                self.state = "wander"
            else:
                self._go_towards(hx, hy, dt)

        else:
            super().step(dt, width, height, rng)
