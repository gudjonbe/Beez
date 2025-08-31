
from __future__ import annotations
import math, random
from typing import Dict, Union, Any

from .roles import RoleDrives, RolePolicy

class Bee:
    """
    Base bee with simple kinematics + role/comms scaffolding.
    """
    SPEED_MIN = 40.0
    SPEED_MAX = 120.0
    TURN_NOISE = 0.5

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float):
        self.id = id
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.heading = math.atan2(vy, vx) if (vx or vy) else 0.0

        # Role state
        self.drives = RoleDrives()
        self.role_policy = RolePolicy()
        self.role: str = "forager"

        # Rendering/classification helpers
        self.kind: str = "bee"     # subclasses set to 'worker', 'queen', etc.
        self.flash_timer: float = 0.0  # short visual pulse when emitting a signal

    # --- movement helpers ---
    def _random_walk(self, dt: float, rng: random.Random) -> None:
        self.heading += (rng.random() - 0.5) * self.TURN_NOISE
        speed = rng.uniform(self.SPEED_MIN, self.SPEED_MAX) * 0.5
        self.vx = speed * math.cos(self.heading)
        self.vy = speed * math.sin(self.heading)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.6) -> None:
        """Steer directly toward (x,y) with a modest speed, shared by subclasses."""
        dx, dy = (x - self.x), (y - self.y)
        angle = math.atan2(dy, dx)
        speed = (self.SPEED_MIN + self.SPEED_MAX) * 0.5 * speed_scale
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.heading = angle

    def _clamp(self, width: int, height: int) -> None:
        self.x = max(4.0, min(width - 4.0, self.x))
        self.y = max(4.0, min(height - 4.0, self.y))

    # --- hooks meant to be overridden ---
    def step(self, dt: float, width: int, height: int, rng: random.Random, world: Any | None = None) -> None:
        self._random_walk(dt, rng)
        self._clamp(width, height)
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

    # --- view ---
    def snapshot(self) -> Dict[str, Union[int, float, str]]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "heading": self.heading,
            "kind": self.kind,
            "flash": self.flash_timer,
            "role": getattr(self, "role", "unknown"),  
        }

