# src/bee_sim/domain/agents/worker.py
from __future__ import annotations
from .bee import Bee


class WorkerBee(Bee):
    """Default worker — baseline motion matches the original demo."""
    SPEED_MIN = 40.0
    SPEED_MAX = 120.0
    TURN_NOISE = 0.4
    RESPAWN_SPEED = 60.0

