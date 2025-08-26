from __future__ import annotations
import math
import random
from typing import Any, TypedDict


class BeeSnapshot(TypedDict):
    id: int
    x: float
    y: float
    heading: float

class Bee:
    SPEED_MIN: float = 40.0
    SPEED_MAX: float = 120.0
    TURN_NOISE: float = 0.4
    RESPAWN_SPEED: float = 60.0

    __slots__ = ("id", "x", "y", "vx", "vy")

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float) -> None:
        self.id = id; self.x = x; self.y = y; self.vx = vx; self.vy = vy

    @property
    def heading(self) -> float:
        return math.atan2(self.vy, self.vx)

    def step(self, dt: float, width: int, height: int, rng: random.Random, world: Any | None = None) -> None:
        """Base wander + bounce; ignores world by default."""
        speed = math.hypot(self.vx, self.vy)
        if speed <= 1e-6:
            angle = rng.random() * math.tau; speed = self.RESPAWN_SPEED
            self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)
        else:
            angle = math.atan2(self.vy, self.vx) + rng.uniform(-self.TURN_NOISE, self.TURN_NOISE) * dt
            speed = min(max(speed + rng.uniform(-2, 2), self.SPEED_MIN), self.SPEED_MAX)
            self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)

        self.x += self.vx * dt; self.y += self.vy * dt
        if self.x < 0: self.x = -self.x; self.vx = abs(self.vx)
        elif self.x > width: self.x = 2*width - self.x; self.vx = -abs(self.vx)
        if self.y < 0: self.y = -self.y; self.vy = abs(self.vy)
        elif self.y > height: self.y = 2*height - self.y; self.vy = -abs(self.vy)

    def snapshot(self) -> BeeSnapshot:   # <-- precise return type
        return {
            "id": self.id,               # int
            "x": self.x,                 # float
            "y": self.y,                 # float
            "heading": self.heading,     # float
        }
