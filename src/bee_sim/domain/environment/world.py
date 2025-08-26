from __future__ import annotations
from typing import Dict, Any
import random

from .flowers import FlowerField
from bee_sim.communication.recruitment import RecruitmentBoard


class World:
    """
    Global state: hive geometry, flowers, communication board, and simple colony metrics.

    New in this version:
    - Intake queue model for nectar: deposit() enqueues; step(dt) processes at a finite rate.
    - Recruitment board (world.comms) is stepped alongside flowers.
    """

    def __init__(self, width: int, height: int, rng: random.Random):
        self.width = width
        self.height = height
        self.rng = rng

        # Hive (centered for now)
        self.hive = (width * 0.5, height * 0.5)
        self.hive_radius = 30.0

        # Environment
        self.flowers = FlowerField(width, height, rng)

        # Communication (waggle-like adverts)
        self.comms = RecruitmentBoard(rng)

        # Colony-level nectar accounting
        self.total_deposited = 0.0   # total nectar that has been fully processed into storage

        # --- Hive intake bottleneck (receivers) ---
        # For MVP we model intake as a single scalar “service rate”.
        self.intake_rate = 4.0       # units of nectar/sec that receivers can process
        self.intake_queue = 0.0      # nectar currently waiting to be processed

    # --------------------------------------------------------------------- #
    # Loop
    # --------------------------------------------------------------------- #
    def step(self, dt: float):
        """Advance world state by dt seconds."""
        if dt <= 0.0:
            return

        # Update environment and communication signals
        self.flowers.step(dt)
        self.comms.step(dt)

        # Process the hive intake queue at a finite rate
        capacity = self.intake_rate * dt
        if capacity <= 0.0 or self.intake_queue <= 0.0:
            return

        processed = min(self.intake_queue, capacity)
        self.intake_queue -= processed
        self.total_deposited += processed

    # --------------------------------------------------------------------- #
    # Mutations (called by UI/agents)
    # --------------------------------------------------------------------- #
    def add_flowers(self, n: int):
        """Add a small random patch of n flowers."""
        self.flowers.add_random(n)

    def add_flower_at(self, x: float, y: float, n: int = 1):
        """Add n flowers near (x, y) with a little jitter."""
        self.flowers.add_at(x, y, n=n)

    def get_flower(self, flower_id: int):
        """Lookup a Flower by id (or None if missing)."""
        return self.flowers.get(flower_id)

    def deposit(self, amount: float):
        """
        Returning foragers call this to hand off nectar.
        Instead of going straight to storage, we enqueue it and let step(dt) process it.
        """
        if amount <= 0.0:
            return
        self.intake_queue += amount

    # --------------------------------------------------------------------- #
    # View / Telemetry
    # --------------------------------------------------------------------- #
    def snapshot(self) -> Dict[str, Any]:
        """Serialize world state for the UI/telemetry."""
        hx, hy = self.hive
        return {
            "hive": {"x": hx, "y": hy, "r": self.hive_radius},

            # Environment
            "flowers": self.flowers.snapshot(),
            "flowers_remaining": self.flowers.remaining(),

            # Colony metrics
            "total_deposited": self.total_deposited,
            "intake_queue": self.intake_queue,
            "intake_rate": self.intake_rate,

            # Communication (kept minimal for now)
            "comms": self.comms.snapshot(),
        }

