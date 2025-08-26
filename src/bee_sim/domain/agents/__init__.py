# src/bee_sim/domain/agents/__init__.py
from __future__ import annotations
import random
from typing import Literal
from .bee import Bee
from .worker import WorkerBee
from .queen import QueenBee
from .drone import DroneBee

BeeKind = Literal["worker", "queen", "drone"]

_KIND_MAP = {
    "worker": WorkerBee,
    "queen": QueenBee,
    "drone": DroneBee,
}

def create_bee(kind: BeeKind, id: int, rng: random.Random, width: int, height: int) -> Bee:
    """Factory for initial placement/velocity with kind-specific speed ranges."""
    cls = _KIND_MAP[kind]
    x = rng.uniform(0, width)
    y = rng.uniform(0, height)
    angle = rng.uniform(0, 6.283185307179586)  # tau
    # Draw an initial speed within the class's min/max
    speed = rng.uniform(cls.SPEED_MIN, cls.SPEED_MAX)
    vx = speed * __import__("math").cos(angle)
    vy = speed * __import__("math").sin(angle)
    return cls(id=id, x=x, y=y, vx=vx, vy=vy)

