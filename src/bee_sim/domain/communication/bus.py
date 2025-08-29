from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Iterable, Tuple, Set, Dict, Any

# Import core types; provide a local alias for SignalKind
from .signals import Signal, SignalBus as _CoreBus, SignalKind
# Back-compat if someone imports SignalKind from bus module
__all__ = ["Signal", "SignalBus", "SignalKind"]

@dataclass
class SignalBus:
    """Compatibility wrapper with width/height fields expected by callers.
    Delegates storage and querying to the core SignalBus implementation.
    """
    width: int
    height: int
    _core: _CoreBus = field(default_factory=_CoreBus, repr=False)

    # Expose the underlying list (read-only by convention)
    @property
    def signals(self) -> List[Signal]:
        return self._core.signals

    # Lifecycle ----------------------------------------------------------
    def emit(self, sig: Signal) -> None:
        self._core.emit(sig)

    def step(self, dt: float) -> None:
        self._core.step(dt)

    # Queries ------------------------------------------------------------
    def strongest(self, x: float, y: float, kinds: Optional[Iterable[str]] = None) -> Optional[Signal]:
        return self._core.strongest(x, y, kinds)

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
        return self._core.query(x, y, kinds, min_strength=min_strength, limit=limit, with_strength=with_strength)

    # Stats / snapshot ---------------------------------------------------
    def snapshot(self, include_kinds: Optional[Set[SignalKind]] = None, max_items: int = 64):
        items = []
        for s in self._core.signals:
            if include_kinds and s.kind not in include_kinds:
                continue
            items.append({
                "k": s.kind, "x": s.x, "y": s.y, "r": s.radius,
                "i": s.intensity, "p": s.payload
            })
            if len(items) >= max_items:
                break
        return items

    def counts(self) -> Dict[str, int]:
        return self._core.counts()
