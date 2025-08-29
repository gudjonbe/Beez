from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, List, Dict, Tuple, Any
import math

# Public type alias for backward compatibility where 'SignalKind' was hinted
SignalKind = str

@dataclass
class Signal:
    """A short-lived signal in space with optional payload.
    Decays over time and vanishes when ttl <= 0.
    """
    kind: str
    x: float
    y: float
    radius: float = 50.0          # effective range (pixels)
    intensity: float = 1.0        # base strength (unitless)
    decay: float = 0.5            # exponential decay rate (1/s)
    ttl: float = 2.0              # time-to-live (s)
    source_id: int = 0            # emitting agent id (optional)
    payload: Optional[Dict[str, Any]] = None

    def falloff(self, px: float, py: float) -> float:
        """Spatial attenuation in [0,1] within radius (cosine falloff).
        1 at center, 0 at radius.
        """
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy)
        if d >= self.radius or self.radius <= 1e-6:
            return 0.0
        t = d / self.radius
        return 0.5 * (1.0 + math.cos(math.pi * t))

    def strength_at(self, px: float, py: float) -> float:
        """Local strength considering spatial falloff and intensity."""
        return self.intensity * self.falloff(px, py)

    # Compatibility alias used by older code paths
    def sense_strength(self, px: float, py: float) -> float:
        return self.strength_at(px, py)

    def step(self, dt: float) -> None:
        """Advance time: exponential intensity decay and ttl countdown."""
        if dt <= 0:
            return
        # Exponential decay of intensity; clamp to 0
        self.intensity *= math.exp(max(-60.0, -max(0.0, self.decay) * dt))
        self.ttl -= dt

    @property
    def alive(self) -> bool:
        return self.ttl > 0.0 and self.intensity > 1e-6


class SignalBus:
    """Holds active signals and provides simple queries.
    API used by the sim:
      - emit(Signal)
      - step(dt)
      - strongest(x, y, kinds: Optional[Iterable[str]])
      - query(x, y, kinds=None, *, min_strength=..., limit=..., with_strength=False)
      - counts()
      - signals (list) for stats/inspection
    """
    def __init__(self):
        self.signals: List[Signal] = []
        self._by_kind: Dict[str, List[Signal]] = {}

    # --- lifecycle ------------------------------------------------------
    def emit(self, sig: Signal) -> None:
        self.signals.append(sig)
        self._by_kind.setdefault(sig.kind, []).append(sig)

    def step(self, dt: float) -> None:
        if not self.signals:
            return
        alive: List[Signal] = []
        self._by_kind.clear()
        for s in self.signals:
            s.step(dt)
            if s.alive:
                alive.append(s)
                self._by_kind.setdefault(s.kind, []).append(s)
        self.signals = alive

    # --- queries --------------------------------------------------------
    def strongest(self, x: float, y: float, kinds: Optional[Iterable[str]] = None) -> Optional[Signal]:
        if kinds is None:
            pool = self.signals
        else:
            pool = []
            for k in kinds:
                pool.extend(self._by_kind.get(k, []))

        best: Optional[Signal] = None
        best_val = 0.0
        for s in pool:
            val = s.strength_at(x, y)
            if val > best_val:
                best_val = val
                best = s
        return best

    def query(
        self,
        x: float,
        y: float,
        kinds: Optional[Iterable[str]] = None,
        *,
        min_strength: float = 0.05,
        limit: int = 16,
        with_strength: bool = False,
    ) -> List[Signal] | List[Tuple[Signal, float]]:
        """Return nearby signals at (x,y), strongest first."""
        if kinds is None:
            pool = self.signals
        else:
            pool = []
            for k in kinds:
                pool.extend(self._by_kind.get(k, []))

        scored: List[Tuple[Signal, float]] = []
        for s in pool:
            val = s.strength_at(x, y)
            if val >= min_strength:
                scored.append((s, val))

        scored.sort(key=lambda sv: sv[1], reverse=True)
        if limit > 0:
            scored = scored[:limit]

        return scored if with_strength else [s for (s, _) in scored]

    def counts(self) -> Dict[str, int]:
        return {k: len(v) for k, v in self._by_kind.items()}
