from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

# Canonical role names used by Worker bees (others can reuse).
Role = Literal["forager","receiver","nurse","fanner","guard","idle"]

@dataclass
class RoleDrives:
    """Continuous propensities for each role; updated from sensed signals."""
    forager: float = 0.0
    receiver: float = 0.0
    nurse: float = 0.0
    fanner: float = 0.0
    guard: float = 0.0

    def decay(self, k: float, dt: float) -> None:
        if dt <= 0: 
            return
        self.forager = max(0.0, self.forager - k*dt)
        self.receiver = max(0.0, self.receiver - k*dt)
        self.nurse = max(0.0, self.nurse - k*dt)
        self.fanner = max(0.0, self.fanner - k*dt)
        self.guard = max(0.0, self.guard - k*dt)

    def score(self, role: Role) -> float:
        return getattr(self, role, 0.0)


class RolePolicy:
    """Hysteresis + minimum-dwell policy to pick a role from drives.

    Avoids thrashing by requiring a margin ('hysteresis') and a min dwell
    time before switching away from the current role.
    """
    def __init__(self, hysteresis: float = 0.25, min_dwell: float = 3.0):
        self.hysteresis = float(hysteresis)
        self.min_dwell = float(min_dwell)
        self.current: Role = "forager"
        self._dwell_t: float = 0.0

    def tick(self, dt: float) -> None:
        self._dwell_t += max(0.0, dt)

    def force(self, role: Role) -> None:
        self.current = role
        self._dwell_t = 0.0

    def choose(self, drives: RoleDrives) -> Role:
        # Find best non-idle role by current scores.
        candidates: list[Role] = ["forager","receiver","nurse","fanner","guard"]
        best = self.current
        best_s = drives.score(self.current)
        for r in candidates:
            s = drives.score(r)
            if s > best_s:
                best, best_s = r, s

        # Switch if we've dwelled long enough and the margin is met.
        if best != self.current and self._dwell_t >= self.min_dwell:
            if best_s >= drives.score(self.current) + self.hysteresis:
                self.force(best)
        return self.current
