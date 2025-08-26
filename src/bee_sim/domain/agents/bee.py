# src/bee_sim/domain/agents/bee.py
from __future__ import annotations
import math
import random
from typing import Dict


class Bee:
    """
    Base Bee entity.
    """

    # Tunables (can be overridden by subclasses)
    SPEED_MIN: float = 40.0
    SPEED_MAX: float = 120.0
    TURN_NOISE: float = 0.4       # radians/sec noise scale
    RESPAWN_SPEED: float = 60.0   # speed if velocity collapses

    __slots__ = ("id", "x", "y", "vx", "vy")

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float) -> None:
        self.id = id
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

    @property
    def heading(self) -> float:
        return math.atan2(self.vy, self.vx)

    def step(self, dt: float, width: int, height: int, rng: random.Random) -> None:
        """Simple wander + edge bounce."""
        speed = math.hypot(self.vx, self.vy)
        if speed <= 1e-6:
            angle = rng.random() * math.tau
            speed = self.RESPAWN_SPEED
            self.vx = speed * math.cos(angle)
            self.vy = speed * math.sin(angle)
        else:
            angle = math.atan2(self.vy, self.vx) + rng.uniform(-self.TURN_NOISE, self.TURN_NOISE) * dt
            # jitter speed a bit and clamp
            speed = min(max(speed + rng.uniform(-2, 2), self.SPEED_MIN), self.SPEED_MAX)
            self.vx = speed * math.cos(angle)
            self.vy = speed * math.sin(angle)

        # integrate
        self.x += self.vx * dt
        self.y += self.vy * dt

        # bounce off walls
        if self.x < 0:
            self.x = -self.x
            self.vx = abs(self.vx)
        elif self.x > width:
            self.x = 2 * width - self.x
            self.vx = -abs(self.vx)

        if self.y < 0:
            self.y = -self.y
            self.vy = abs(self.vy)
        elif self.y > height:
            self.y = 2 * height - self.y
            self.vy = -abs(self.vy)

    def snapshot(self) -> Dict[str, float]:
        """Return a view-friendly dict. The API layer will convert this to its dataclasses."""
        return {"id": self.id, "x": self.x, "y": self.y, "heading": self.heading}

