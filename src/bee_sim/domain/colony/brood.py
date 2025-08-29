from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import random

# ---- Tunables (sim-seconds; keep short for interactive sim) -------------------
EGG_DURATION   = 40.0   # sec to become larva
LARVA_DURATION = 80.0   # sec to become pupa (with care; slower without)
PUPA_DURATION  = 120.0  # sec to emerge

# One nurse can deliver this much "care" per second.
CARE_PER_NURSE = 1.0

# Full-speed development requires this care per larva per second.
CARE_REQ_PER_LARVA = 0.3

# Mortality when care is insufficient (per-second hazard applied to larvae).
UNCARED_LARVA_HAZARD = 0.002

@dataclass
class Cohort:
    count: int
    age: float = 0.0  # seconds

@dataclass
class Brood:
    """Simple brood pipeline: eggs -> larvae -> pupae -> hatch."""
    eggs: List[Cohort] = field(default_factory=list)
    larvae: List[Cohort] = field(default_factory=list)
    pupae: List[Cohort] = field(default_factory=list)

    _care_accum: float = 0.0  # nurse care added this tick

    def add_eggs(self, n: int, rng: Optional[random.Random] = None) -> None:
        if n <= 0:
            return
        jitter = 0.0 if rng is None else rng.uniform(0.0, 1.0)  # anti-lockstep
        self.eggs.append(Cohort(n, age=jitter))

    # ---- demand / stats -----------------------------------------------------
    def larvae_count(self) -> int: return sum(c.count for c in self.larvae)
    def eggs_count(self) -> int:   return sum(c.count for c in self.eggs)
    def pupae_count(self) -> int:  return sum(c.count for c in self.pupae)
    def brood_counts(self) -> dict:
        return {"eggs": self.eggs_count(), "larvae": self.larvae_count(), "pupae": self.pupae_count()}
    def nurse_target(self, nurses_per_larva: float) -> float:
        return self.larvae_count() * nurses_per_larva

    def add_care(self, care_units: float) -> None:
        if care_units > 0:
            self._care_accum += float(care_units)

    def tick(self, dt: float, rng: random.Random) -> int:
        """Advance by dt seconds. Return number of newly hatched bees."""
        if dt <= 0:
            self._care_accum = 0.0
            return 0

        # Eggs → Larvae
        for c in self.eggs: c.age += dt
        promote = [c for c in self.eggs if c.age >= EGG_DURATION]
        if promote:
            for c in promote: self.larvae.append(Cohort(c.count, age=0.0))
            self.eggs = [c for c in self.eggs if c.age < EGG_DURATION]

        # Nurse care distribution
        larvae_total = self.larvae_count()
        care_per_larva = 0.0 if larvae_total == 0 else (self._care_accum / larvae_total) / max(1e-9, dt)
        speed_multiplier = min(1.0, care_per_larva / CARE_REQ_PER_LARVA)
        baseline = 0.25  # some progress even with poor care
        hazard = 0.0
        if larvae_total and care_per_larva < CARE_REQ_PER_LARVA:
            deficit = 1.0 - (care_per_larva / CARE_REQ_PER_LARVA)
            hazard = UNCARED_LARVA_HAZARD * deficit

        # Age larvae; mortality; Larvae → Pupae
        for c in self.larvae:
            c.age += dt * (baseline + 0.75 * speed_multiplier)
            if hazard > 0.0 and c.count > 0:
                lam = hazard * dt * c.count  # cheap Poisson-ish expectation
                deaths = min(c.count, int(lam + 0.5))
                c.count -= deaths
        promote = [c for c in self.larvae if c.age >= LARVA_DURATION and c.count > 0]
        if promote:
            for c in promote: self.pupae.append(Cohort(c.count, age=0.0))
            self.larvae = [c for c in self.larvae if c.count > 0 and c.age < LARVA_DURATION]

        # Pupae → Adults
        for c in self.pupae: c.age += dt
        emerge = [c for c in self.pupae if c.age >= PUPA_DURATION]
        hatched = sum(c.count for c in emerge) if emerge else 0
        self.pupae = [c for c in self.pupae if c.age < PUPA_DURATION]

        self._care_accum = 0.0
        return hatched
