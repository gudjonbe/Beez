from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Tuple
import math, random

Vec2 = Tuple[float, float]

@dataclass
class BeeView:
    id: int
    x: float
    y: float
    heading: float

@dataclass
class WorldView:
    t: float
    bees: List[BeeView]
    paused: bool
    speed: float
    width: int
    height: int

class Bee:
    __slots__ = ("id", "x", "y", "vx", "vy")
    def __init__(self, id: int, x: float, y: float, vx: float, vy: float):
        self.id = id; self.x = x; self.y = y; self.vx = vx; self.vy = vy

    def step(self, dt: float, width: int, height: int):
        speed = math.hypot(self.vx, self.vy)
        if speed <= 1e-6:
            angle = random.random() * math.tau; speed = 60.0
            self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)
        else:
            angle = math.atan2(self.vy, self.vx) + random.uniform(-0.4, 0.4) * dt
            speed = min(max(speed + random.uniform(-2, 2), 40.0), 120.0)
            self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)
        self.x += self.vx * dt; self.y += self.vy * dt
        if self.x < 0: self.x = -self.x; self.vx = abs(self.vx)
        elif self.x > width: self.x = 2*width - self.x; self.vx = -abs(self.vx)
        if self.y < 0: self.y = -self.y; self.vy = abs(self.vy)
        elif self.y > height: self.y = 2*height - self.y; self.vy = -abs(self.vy)

    def view(self) -> BeeView:
        return BeeView(id=self.id, x=self.x, y=self.y, heading=math.atan2(self.vy, self.vx))

class SimController:
    """Small controller suitable for the first GUI test."""
    def __init__(self, width: int = 960, height: int = 540, seed: int | None = None):
        self.width = width; self.height = height; self.rng = random.Random(seed)
        self._t = 0.0; self._next_id = 1; self._bees: list[Bee] = []
        self._paused = False; self._speed = 1.0
        self.add_bees(5)

    def set_paused(self, paused: bool): self._paused = paused
    def toggle_paused(self) -> bool: self._paused = not self._paused; return self._paused
    def set_speed(self, speed: float): self._speed = max(0.0, min(4.0, float(speed)))

    def add_bees(self, n: int):
        for _ in range(n):
            x = self.rng.uniform(0, self.width); y = self.rng.uniform(0, self.height)
            angle = self.rng.uniform(0, math.tau); speed = self.rng.uniform(40.0, 100.0)
            vx = speed * math.cos(angle); vy = speed * math.sin(angle)
            b = Bee(self._next_id, x, y, vx, vy); self._next_id += 1; self._bees.append(b)

    def step(self, dt: float):
        if self._paused or dt <= 0.0: return
        dt *= self._speed; self._t += dt
        for b in self._bees: b.step(dt, self.width, self.height)

    def get_view(self) -> dict:
        return {
            "t": self._t,
            "paused": self._paused,
            "speed": self._speed,
            "width": self.width,
            "height": self.height,
            "bees": [asdict(b.view()) for b in self._bees],
        }
