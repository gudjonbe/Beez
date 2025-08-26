from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable, Set
import random, math

@dataclass
class Flower:
    id: int
    x: float
    y: float
    nectar: float
    cap: float
    regen_rate: float
    reserved: bool = False
    ever_visited: bool = False  # optional: track if ever collected

    def frac(self) -> float:
        if self.cap <= 0:
            return 0.0
        return max(0.0, min(1.0, self.nectar / self.cap))

    def step(self, dt: float):
        if dt <= 0:
            return
        if self.nectar < self.cap:
            # saturating growth: faster when empty, slower near capacity
            growth = self.regen_rate * (1.0 - self.frac()) * dt
            self.nectar = min(self.cap, self.nectar + growth)

    @property
    def available(self) -> bool:
        # "worth visiting" threshold
        return self.nectar >= 0.75


class FlowerField:
    def __init__(self, width: int, height: int, rng: random.Random,
                 n_patches: int = 3, flowers_per_patch: int = 12):
        self.width = width
        self.height = height
        self.rng = rng
        self.flowers: List[Flower] = []
        self._next_id = 1

        for _ in range(n_patches):
            self.add_patch(
                cx=rng.uniform(80, width - 80),
                cy=rng.uniform(80, height - 80),
                radius=rng.uniform(40, 120),
                n=flowers_per_patch,
            )

    # ---- generation helpers ----
    def _new_flower(self, x: float, y: float) -> Flower:
        cap = self.rng.uniform(2.0, 6.0)
        nectar = self.rng.uniform(0.8, cap)
        regen_rate = self.rng.uniform(0.1, 0.3)
        f = Flower(self._next_id, x, y, nectar=nectar, cap=cap, regen_rate=regen_rate)
        self._next_id += 1
        return f

    def add_patch(self, cx: float, cy: float, radius: float, n: int):
        for _ in range(n):
            angle = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(0, radius)
            x = max(8.0, min(self.width - 8.0, cx + r * math.cos(angle)))
            y = max(8.0, min(self.height - 8.0, cy + r * math.sin(angle)))
            self.flowers.append(self._new_flower(x, y))

    def add_random(self, n: int):
        cx = self.rng.uniform(80, self.width - 80)
        cy = self.rng.uniform(80, self.height - 80)
        radius = self.rng.uniform(30, 90)
        self.add_patch(cx, cy, radius, n)

    def add_at(self, x: float, y: float, n: int = 1, jitter: float = 10.0):
        for _ in range(n):
            jx = self.rng.uniform(-jitter, jitter)
            jy = self.rng.uniform(-jitter, jitter)
            xx = max(8.0, min(self.width - 8.0, x + jx))
            yy = max(8.0, min(self.height - 8.0, y + jy))
            self.flowers.append(self._new_flower(xx, yy))

    # ---- update step ----
    def step(self, dt: float):
        for f in self.flowers:
            f.step(dt)

    # ---- reservation & collection ----
    def _iter_available(self):
        return (f for f in self.flowers if (not f.reserved) and f.available)

    def reserve_nearest(self, x: float, y: float, avoid_ids: Set[int] | None = None):
        best = None
        best_d2 = 0.0
        for f in self._iter_available():
            if avoid_ids and f.id in avoid_ids:
                continue
            d2 = (f.x - x) * (f.x - x) + (f.y - y) * (f.y - y)
            if best is None or d2 < best_d2:
                best, best_d2 = f, d2
        if best:
            best.reserved = True
        return best

    def collect_from(self, flower_id: int, amount: float) -> float:
        for f in self.flowers:
            if f.id == flower_id:
                got = min(amount, max(0.0, f.nectar))
                f.nectar -= got
                if got > 0:
                    f.ever_visited = True
                f.reserved = False
                return got
        return 0.0

    def release_reservation(self, flower_id: int) -> None:
        for f in self.flowers:
            if f.id == flower_id:
                f.reserved = False
                return

    # ---- LOOKUP (fix) ----
    def get(self, flower_id: int) -> Optional[Flower]:
        """Return Flower by id, or None."""
        for f in self.flowers:
            if f.id == flower_id:
                return f
        return None

    # ---- metrics & view ----
    def remaining(self) -> int:
        return sum(1 for f in self.flowers if f.available)

    def snapshot(self) -> List[dict]:
        out = []
        for f in self.flowers:
            frac = f.frac()
            visited = f.ever_visited or (frac < 0.05)
            out.append({"id": f.id, "x": f.x, "y": f.y, "frac": frac, "visited": visited})
        return out

