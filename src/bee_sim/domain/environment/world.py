from __future__ import annotations
from typing import Dict, Any
import random
from .flowers import FlowerField

class World:
    """Holds global state: hive, flowers, simple metrics."""
    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width
        self.height = height
        self.rng = rng

        self.hive = (width * 0.5, height * 0.5)
        self.hive_radius = 30.0

        self.flowers = FlowerField(width, height, rng)
        self.total_deposited = 0.0

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

