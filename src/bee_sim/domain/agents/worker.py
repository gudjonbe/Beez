from __future__ import annotations
from typing import Optional, Any
import math
from .bee import Bee

class WorkerBee(Bee):
    """Worker with a tiny foraging state machine."""
    SPEED_MIN = 40.0
    SPEED_MAX = 120.0
    TURN_NOISE = 0.4
    RESPAWN_SPEED = 60.0

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float):
        super().__init__(id, x, y, vx, vy)
        self.state: str = "wander"
        self.target_flower_id: Optional[int] = None
        self.carry: float = 0.0
        self.capacity: float = 2.0

    def step(self, dt: float, width: int, height: int, rng, world: Any | None = None) -> None:
        if world is None:
            return super().step(dt, width, height, rng)

        if self.state == "wander":
            if world.flowers.remaining() > 0:
                f = world.flowers.reserve_next_unvisited()
                if f:
                    self.target_flower_id = f.id
                    self.state = "to_flower"
            super().step(dt, width, height, rng)

        elif self.state == "to_flower":
            f = world.get_flower(self.target_flower_id) if self.target_flower_id else None
            if not f or f.visited or f.nectar <= 0.0:
                if self.target_flower_id:
                    world.flowers.release_reservation(self.target_flower_id)
                self.target_flower_id = None
                self.state = "wander"
                return

            dx, dy = (f.x - self.x), (f.y - self.y)
            dist = math.hypot(dx, dy)
            if dist < 8.0:
                self.carry = min(self.capacity, f.nectar)
                world.flowers.mark_collected(f.id)
                self.state = "to_hive"
            else:
                angle = math.atan2(dy, dx)
                speed = (self.SPEED_MIN + self.SPEED_MAX) * 0.6
                self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)
                self.x += self.vx * dt; self.y += self.vy * dt

        elif self.state == "to_hive":
            hx, hy = world.hive
            dx, dy = (hx - self.x), (hy - self.y)
            dist = math.hypot(dx, dy)
            if dist < (world.hive_radius + 8.0):
                world.deposit(self.carry)
                self.carry = 0.0
                self.target_flower_id = None
                self.state = "wander"
            else:
                angle = math.atan2(dy, dx)
                speed = (self.SPEED_MIN + self.SPEED_MAX) * 0.6
                self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)
                self.x += self.vx * dt; self.y += self.vy * dt

        else:
            super().step(dt, width, height, rng)

