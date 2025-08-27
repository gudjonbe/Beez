from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Dict, Any, Optional
import math

SignalKind = Literal[
    "queen_mandibular",
    "nasonov",
    "alarm",
    "brood",
    "forager_primer",
    "waggle",
    "round",
    "tremble",
    "shake",
    "stop",
    "worker_piping",
    "queen_piping",
    "trophallaxis",
    "fanning",
    "thermal",
]

@dataclass
class Signal:
    kind: SignalKind
    x: float
    y: float
    radius: float
    intensity: float
    decay: float = 0.5
    ttl: float = 5.0
    source_id: Optional[int] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def step(self, dt: float) -> None:
        if dt <= 0: return
        self.intensity *= math.exp(-self.decay * dt)
        self.ttl -= dt

    @property
    def alive(self) -> bool:
        return self.ttl > 0 and self.intensity > 1e-3

    def sense_strength(self, qx: float, qy: float) -> float:
        dx, dy = (qx - self.x), (qy - self.y)
        r = max(1e-6, self.radius)
        falloff = 1.0 / (1.0 + (dx*dx + dy*dy) / (r*r))
        return self.intensity * falloff
