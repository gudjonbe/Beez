from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random, math

@dataclass
class Flower:
    id: int
    x: float
    y: float
    nectar: float
    visited: bool = False
    reserved: bool = False

class FlowerField:
    """Generate a few circular patches and manage reservations/visits."""
    def __init__(self, width: int, height: int, rng: random.Random,
                 n_patches: int = 3, flowers_per_patch: int = 12):
        self.width = width
        self.height = height
        self.rng = rng
        self.flowers: List[Flower] = []
        self._next_id = 1

        for _ in range(n_patches):
            cx = rng.uniform(80, width - 80)
            cy = rng.uniform(80, height - 80)
            radius = rng.uniform(40, 120)
            for _ in range(flowers_per_patch):
                angle = rng.uniform(0, math.tau)
                r = rng.uniform(0, radius)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                nectar = rng.uniform(1.0, 3.0)
                self.flowers.append(Flower(self._next_id, x, y, nectar))
                self._next_id += 1

    def get(self, flower_id: int) -> Optional[Flower]:
        for f in self.flowers:
            if f.id == flower_id:
                return f
        return None

    def reserve_next_unvisited(self) -> Optional[Flower]:
        for f in self.flowers:
            if not f.visited and not f.reserved and f.nectar > 0.0:
                f.reserved = True
                return f
        return None

    def mark_collected(self, flower_id: int) -> None:
        f = self.get(flower_id)
        if f:
            f.nectar = 0.0
            f.visited = True
            f.reserved = False

    def release_reservation(self, flower_id: int) -> None:
        f = self.get(flower_id)
        if f and not f.visited:
            f.reserved = False

    def remaining(self) -> int:
        return sum(1 for f in self.flowers if not f.visited and f.nectar > 0.0)

    def snapshot(self) -> List[dict]:
        return [
            {"id": f.id, "x": f.x, "y": f.y, "visited": f.visited, "nectar": f.nectar}
            for f in self.flowers
        ]

