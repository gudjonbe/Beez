from __future__ import annotations
from typing import List, Optional, Set
from dataclasses import dataclass, field

from .signals import Signal, SignalKind

@dataclass
class SignalBus:
    width: int
    height: int
    signals: List[Signal] = field(default_factory=list)

    def emit(self, sig: Signal) -> None:
        self.signals.append(sig)

    def step(self, dt: float) -> None:
        for s in self.signals:
            s.step(dt)
        self.signals = [s for s in self.signals if s.alive]

    def query(self, x: float, y: float, kinds: Optional[Set[SignalKind]] = None) -> List[Signal]:
        out = []
        for s in self.signals:
            if kinds and s.kind not in kinds:
                continue
            if (s.x - x)**2 + (s.y - y)**2 <= (s.radius * 1.2)**2:
                out.append(s)
        return out

    def strongest(self, x: float, y: float, kinds: Optional[Set[SignalKind]] = None) -> Optional[Signal]:
        best = None
        best_w = 0.0
        for s in self.query(x, y, kinds):
            w = s.sense_strength(x, y)
            if w > best_w:
                best_w = w; best = s
        return best

    def snapshot(self, include_kinds: Optional[Set[SignalKind]] = None, max_items: int = 64):
        items = []
        for s in self.signals:
            if include_kinds and s.kind not in include_kinds:
                continue
            items.append({"k": s.kind, "x": s.x, "y": s.y, "r": s.radius, "i": s.intensity, "p": s.payload})
            if len(items) >= max_items: break
        return items
