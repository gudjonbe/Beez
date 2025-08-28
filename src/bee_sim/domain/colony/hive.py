from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Hive:
    """Hive model with zones and a receiver queue."""
    x: float
    y: float
    radius: float

    receiver_queue: float = 0.0
    brood_frac: float = 0.55  # brood zone as fraction of radius

    @property
    def entrance_xy(self) -> tuple[float, float]:
        # 12 o'clock entrance
        return (self.x, self.y - self.radius)

    @property
    def brood_radius(self) -> float:
        return self.radius * self.brood_frac

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

    def snapshot(self) -> dict:
        return {"x": self.x, "y": self.y, "r": self.radius, "queue": self.receiver_queue}

