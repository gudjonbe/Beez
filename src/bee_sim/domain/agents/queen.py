# src/bee_sim/domain/agents/queen.py
from __future__ import annotations
from .bee import Bee


class QueenBee(Bee):
    """Slow, deliberate movement — placeholder until hive constraints are modeled."""
    SPEED_MIN = 10.0
    SPEED_MAX = 40.0
    TURN_NOISE = 0.2
    RESPAWN_SPEED = 20.0

