from __future__ import annotations
from typing import Dict, Any
import random

from .flowers import FlowerField

class World:
    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width
        self.height = height
        self.rng = rng
        self.hive = (width * 0.5, height * 0.5)
        self.hive_radius = 30.0
        self.flowers = FlowerField(width, height, rng)
        self.total_deposited = 0.0

    def step(self, dt: float):
        self.flowers.step(dt)

    def add_flowers(self, n: int):
        self.flowers.add_random(n)

    def add_flower_at(self, x: float, y: float, n: int = 1):
        self.flowers.add_at(x, y, n=n)

    def get_flower(self, flower_id: int):
        return self.flowers.get(flower_id)

    def deposit(self, amount: float):
        self.total_deposited += amount

    def snapshot(self) -> Dict[str, Any]:
        hx, hy = self.hive
        return {
            "hive": {"x": hx, "y": hy, "r": self.hive_radius},
            "flowers": self.flowers.snapshot(),
            "flowers_remaining": self.flowers.remaining(),
            "total_deposited": self.total_deposited,
        }
