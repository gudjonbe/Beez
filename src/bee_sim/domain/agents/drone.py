# src/bee_sim/domain/agents/drone.py
from __future__ import annotations
from .bee import Bee


class DroneBee(Bee):
    SPEED_MIN = 60.0
    SPEED_MAX = 160.0
    TURN_NOISE = 0.35
    RESPAWN_SPEED = 80.0

