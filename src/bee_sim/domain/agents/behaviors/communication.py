from __future__ import annotations
from typing import Dict, Set
from dataclasses import dataclass

# Signals we aggregate into perception.
SENSE_KEYS: Set[str] = {
    "queen_mandibular","brood","forager_primer","waggle","round","tremble",
    "shake","stop","nasonov","alarm","worker_piping","queen_piping","fanning","thermal"
}

@dataclass
class SenseConfig:
    # Max number of signals to sum per kind (perf guard).
    max_per_kind: int = 8

DEFAULT_SENSE = SenseConfig()

def sense_signals(x: float, y: float, world, cfg: SenseConfig = DEFAULT_SENSE) -> Dict[str, float]:
    """Aggregate sensed strength per kind near (x,y)."""
    out: Dict[str, float] = {}
    bus = getattr(world, "signals", None)
    if bus is None:
        return out
    sigs = bus.query(x, y, kinds=None)
    counts: Dict[str, int] = {}
    for s in sigs:
        k = getattr(s, "kind", None)
        if not isinstance(k, str) or k not in SENSE_KEYS:
            continue
        c = counts.get(k, 0)
        if c >= cfg.max_per_kind:
            continue
        counts[k] = c + 1
        out[k] = out.get(k, 0.0) + s.sense_strength(x, y)
    return out

# Weights from sensed kinds to drive deltas per role.
WEIGHTS: Dict[str, Dict[str, float]] = {
    "forager": {
        "waggle": +0.9, "round": +0.5, "brood": -0.3, "forager_primer": -0.3,
        "tremble": -0.4, "stop": -0.8, "queen_mandibular": +0.05
    },
    "receiver": {
        "tremble": +0.8, "brood": +0.2, "forager_primer": +0.2
    },
    "nurse": {
        "brood": +0.9, "forager_primer": +0.3, "queen_mandibular": +0.1
    },
    "fanner": {
        "nasonov": +0.7, "thermal": +0.3, "queen_mandibular": +0.1
    },
    "guard": {
        "alarm": +1.0, "queen_mandibular": -0.1
    }
}

def drives_from_senses(drives, senses: Dict[str, float], dt: float, k_decay: float = 0.15) -> None:
    """Update drives in-place from sensed strengths (with simple decay)."""
    # Decay first
    drives.decay(k_decay, dt)

    def accum(role: str, kind: str, w: float):
        v = senses.get(kind, 0.0)
        if v <= 0.0: 
            return 0.0
        return w * v * dt

    for role, table in WEIGHTS.items():
        delta = 0.0
        for kind, w in table.items():
            delta += accum(role, kind, w)
        val = max(0.0, min(5.0, getattr(drives, role) + delta))
        setattr(drives, role, val)
