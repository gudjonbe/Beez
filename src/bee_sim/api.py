# src/bee_sim/api.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import random

from bee_sim.domain.agents import create_bee, Bee, BeeKind 


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


class SimController:
    """Controller driving a simple bee swarm for the demo UI.

    The controller depends on the domain layer for entities, and exposes view
    dataclasses to the UI/network layers. No domain imports of this module.
    """
    def __init__(self, width: int = 960, height: int = 540, seed: int | None = None):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self._t = 0.0
        self._next_id = 1
        self._bees: list[Bee] = []
        self._paused = False
        self._speed = 1.0
        self.add_bees(5)  # default: workers

    # --- control
    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def toggle_paused(self) -> bool:
        self._paused = not self._paused
        return self._paused

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.0, min(4.0, float(speed)))

            
    def add_bees(self, n: int, kind: "BeeKind" = "worker") -> None:
        for _ in range(n):
            b = create_bee(kind, id=self._next_id, rng=self.rng, width=self.width, height=self.height)
            self._next_id += 1
            self._bees.append(b)


    # --- loop
    def step(self, dt: float) -> None:
        if self._paused or dt <= 0.0:
            return
        dt *= self._speed
        self._t += dt
        for b in self._bees:
            b.step(dt, self.width, self.height, self.rng)

    # --- view
    def get_view(self) -> dict:
        bees_view = [BeeView(**b.snapshot()) for b in self._bees]
        view = WorldView(
            t=self._t,
            bees=bees_view,
            paused=self._paused,
            speed=self._speed,
            width=self.width,
            height=self.height,
        )
        # Return a plain dict for JSON encoding
        return {
            "t": view.t,
            "paused": view.paused,
            "speed": view.speed,
            "width": view.width,
            "height": view.height,
            "bees": [bv.__dict__ for bv in view.bees],
        }

