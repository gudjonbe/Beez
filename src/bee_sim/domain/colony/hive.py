from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from bee_sim.domain.colony.brood import Brood, CARE_PER_NURSE
from bee_sim.domain.communication.signals import Signal

@dataclass
class Hive:
    """Hive model with zones, receiver queue, and brood pipeline."""
    x: float
    y: float
    radius: float

    receiver_queue: float = 0.0
    brood_frac: float = 0.55       # brood zone as fraction of radius
    nurse_per_larva: float = 0.08  # target nurses per larva (tune)

    # Brood internals
    _brood: Brood = field(default_factory=Brood)
    _brood_emit_acc: float = 0.0
    _care_buffer: float = 0.0
    _nurses_current: int = 0

    @property
    def entrance_xy(self) -> tuple[float, float]:
        # 12 o'clock entrance
        return (self.x, self.y - self.radius)

    @property
    def brood_radius(self) -> float:
        return self.radius * self.brood_frac

    # --- receiver queue -----------------------------------------------------
    def enqueue(self, nectar: float) -> None:
        if nectar > 0:
            self.receiver_queue += float(nectar)

    def drain(self, dt: float, rate: float) -> float:
        """Drain queue by 'rate' units/sec. Returns the amount drained."""
        if dt <= 0 or rate <= 0 or self.receiver_queue <= 1e-9:
            return 0.0
        amount = min(self.receiver_queue, rate * dt)
        self.receiver_queue -= amount
        return amount

    # --- brood API ----------------------------------------------------------
    def add_eggs(self, n: int, rng) -> None:
        if self._brood and n > 0:
            self._brood.add_eggs(n, rng)

    def nurse_target(self) -> float:
        if self._brood:
            return self._brood.nurse_target(self.nurse_per_larva)
        return 0.0

    def set_nurses_current(self, n: int) -> None:
        self._nurses_current = max(0, int(n))

    def nurse_care(self, dt: float, nurses: Optional[int] = None, per_bee: float = CARE_PER_NURSE) -> None:
        if nurses is None:
            nurses = 1
        self._care_buffer += max(0.0, float(nurses) * float(per_bee) * float(dt))

    def tick_brood(self, dt: float, rng, signals_bus=None) -> int:
        """Advance brood and emit demand-based 'brood' signal. Returns hatched count."""
        if not self._brood:
            return 0
        if self._care_buffer > 0.0:
            self._brood.add_care(self._care_buffer)
            self._care_buffer = 0.0

        hatched = self._brood.tick(dt, rng)

        # Demand-scaled 'brood' signal to recruit nurses when in deficit
        target = self.nurse_target()
        deficit = max(0.0, target - float(self._nurses_current))
        demand = 0.0 if target <= 0 else min(1.0, deficit / max(1.0, target))
        self._brood_emit_acc += dt
        if signals_bus is not None and demand > 0.01 and self._brood_emit_acc >= 0.2:
            self._brood_emit_acc = 0.0
            signals_bus.emit(Signal(
                kind="brood",
                x=self.x, y=self.y,
                radius=self.brood_radius,
                intensity=0.8 * demand,
                decay=0.2, ttl=0.6, source_id=0
            ))
        return hatched

    def brood_snapshot(self) -> dict:
        if not self._brood:
            return {"eggs": 0, "larvae": 0, "pupae": 0, "nurse_target": 0, "nurses_current": self._nurses_current}
        data = self._brood.brood_counts()
        data["nurse_target"] = self.nurse_target()
        data["nurses_current"] = self._nurses_current
        return data

    def snapshot(self) -> dict:
        return {"x": self.x, "y": self.y, "r": self.radius, "queue": self.receiver_queue}
