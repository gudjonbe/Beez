from __future__ import annotations
from typing import Optional, Any, Deque
from collections import deque
import math, random

from .bee import Bee
from .roles import Role
from .behaviors.communication import sense_signals, drives_from_senses

class WorkerBee(Bee):
    """Worker with role-based behavior, foraging, and basic communication."""
    SPEED_MIN = 40.0
    SPEED_MAX = 120.0
    TURN_NOISE = 0.35
    RESPAWN_SPEED = 60.0

    VISIT_QUANTA = 0.8
    AVOID_MEMORY = 16
    WAGGLE_THRESHOLD = 1.0
    WAGGLE_TTL = 6.0

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float):
        super().__init__(id, x, y, vx, vy)
        self.state: str = "wander"
        self.target_flower_id: Optional[int] = None
        self.carry: float = 0.0
        self.capacity: float = 3.0
        self._avoid: Deque[int] = deque(maxlen=self.AVOID_MEMORY)
        self._recruit_target: Optional[tuple[float, float]] = None
        self._last_flower_xy: Optional[tuple[float, float]] = None

    # --- shared helpers ---
    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.6):
        dx, dy = (x - self.x), (y - self.y)
        angle = math.atan2(dy, dx)
        speed = (self.SPEED_MIN + self.SPEED_MAX) * speed_scale
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def _inside_hive(self, world) -> bool:
        hx, hy = world.hive
        return math.hypot(self.x - hx, self.y - hy) <= (world.hive_radius + 5.0)

    # --- role sub-behaviors ---
    def _behave_forager(self, dt: float, width: int, height: int, rng: random.Random, world: Any):
        if self.state == "wander":
            # waggle-follow: strongest waggle sampled in hive sets a soft target
            if self._inside_hive(world):
                sig = world.signals.strongest(self.x, self.y, kinds={"waggle"})
                if sig and isinstance(sig.payload, dict):
                    tx = sig.payload.get("tx"); ty = sig.payload.get("ty")
                    if isinstance(tx, (int, float)) and isinstance(ty, (int, float)):
                        self._recruit_target = (float(tx), float(ty))
            if self.carry + 1e-6 < self.capacity and world.flowers.remaining() > 0:
                if self._recruit_target:
                    rx, ry = self._recruit_target
                    self._go_towards(rx, ry, dt*0.5, speed_scale=0.9)
                f = world.flowers.reserve_nearest(self.x, self.y, set(self._avoid))
                if f:
                    self.target_flower_id = f.id
                    self.state = "to_flower"
                    self._recruit_target = None
                    return
            super().step(dt, width, height, rng)

        elif self.state == "to_flower":
            f = world.get_flower(self.target_flower_id) if self.target_flower_id else None
            if not f or not f.available:
                if self.target_flower_id is not None:
                    world.flowers.release_reservation(self.target_flower_id)
                self.target_flower_id = None
                self.state = "wander"
                return
            dist = math.hypot(f.x - self.x, f.y - self.y)
            if dist < 10.0:
                got = world.flowers.collect_from(f.id, amount=min(self.VISIT_QUANTA, self.capacity - self.carry))
                self.carry += got
                if got > 0.0:
                    self._avoid.append(f.id)
                    self._last_flower_xy = (f.x, f.y)
                if (self.carry + 1e-6) < self.capacity and world.flowers.remaining() > 0:
                    nf = world.flowers.reserve_nearest(self.x, self.y, set(self._avoid))
                    if nf:
                        self.target_flower_id = nf.id
                        self.state = "to_flower"
                        return
                self.target_flower_id = None
                self.state = "to_hive"
            else:
                self._go_towards(f.x, f.y, dt)

        elif self.state == "to_hive":
            hx, hy = world.hive
            dist = math.hypot(hx - self.x, hy - self.y)
            if dist < (world.hive_radius + 10.0):
                if self.carry > 0.0:
                    world.deposit(self.carry)
                    if self.carry >= self.WAGGLE_THRESHOLD and self._last_flower_xy:
                        lx, ly = self._last_flower_xy
                        from bee_sim.domain.communication.signals import Signal
                        world.signals.emit(Signal(
                            kind="waggle", x=hx, y=hy, radius=40.0,
                            intensity=min(2.5, 0.8 + 0.4 * self.carry),
                            decay=0.35, ttl=self.WAGGLE_TTL, source_id=self.id,
                            payload={"tx": float(lx), "ty": float(ly)}
                        ))
                    self.carry = 0.0
                self.state = "wander"
            else:
                self._go_towards(hx, hy, dt)
        else:
            super().step(dt, width, height, rng)

    def _behave_receiver(self, dt: float, width: int, height: int, rng: random.Random, world: Any):
        # stay around hive center; slow wander
        hx, hy = world.hive
        if math.hypot(self.x - hx, self.y - hy) > world.hive_radius * 0.7:
            self._go_towards(hx, hy, dt, speed_scale=0.5)
        else:
            self._random_walk(dt*0.5, rng)
        self._clamp(width, height)

    def _behave_nurse(self, dt: float, width: int, height: int, rng: random.Random, world: Any):
        # brood area ~ center; stronger attraction
        hx, hy = world.hive
        if math.hypot(self.x - hx, self.y - hy) > world.hive_radius * 0.6:
            self._go_towards(hx, hy, dt, speed_scale=0.6)
        else:
            self._random_walk(dt*0.4, rng)
        self._clamp(width, height)

    def _behave_fanner(self, dt: float, width: int, height: int, rng: random.Random, world: Any):
        # go to entrance (top arc of hive circle) and emit nasonov/fanning periodically
        hx, hy = world.hive
        ex, ey = hx, hy - world.hive_radius  # 12 o'clock entrance
        if math.hypot(self.x - ex, self.y - ey) > 8.0:
            self._go_towards(ex, ey, dt, speed_scale=0.7)
        else:
            self._random_walk(dt*0.3, rng)
            # emit light nasonov/fanning
            from bee_sim.domain.communication.signals import Signal
            world.signals.emit(Signal(kind="nasonov", x=ex, y=ey, radius=60.0, intensity=0.6, decay=0.5, ttl=1.2, source_id=self.id))
            world.signals.emit(Signal(kind="fanning",  x=ex, y=ey, radius=50.0, intensity=0.4, decay=0.6, ttl=1.0, source_id=self.id))
        self._clamp(width, height)

    def _behave_guard(self, dt: float, width: int, height: int, rng: random.Random, world: Any):
        # patrol entrance rim
        hx, hy = world.hive
        ex, ey = hx, hy - world.hive_radius
        if math.hypot(self.x - ex, self.y - ey) > 12.0:
            self._go_towards(ex, ey, dt, speed_scale=0.8)
        else:
            self._random_walk(dt*0.4, rng)
        self._clamp(width, height)

    # --- main step ---
    def step(self, dt: float, width: int, height: int, rng: random.Random, world: Any | None = None) -> None:
        if world is None:
            return super().step(dt, width, height, rng)

        # 1) Perceive signals and update drives
        senses = sense_signals(self.x, self.y, world)
        drives_from_senses(self.drives, senses, dt)

        # 2) Pick role with hysteresis + dwell
        self.role_policy.tick(dt)
        role: Role = self.role_policy.choose(self.drives)
        self.role = role

        # 3) Execute role behavior
        if role == "forager":
            self._behave_forager(dt, width, height, rng, world)
        elif role == "receiver":
            self._behave_receiver(dt, width, height, rng, world)
        elif role == "nurse":
            self._behave_nurse(dt, width, height, rng, world)
        elif role == "fanner":
            self._behave_fanner(dt, width, height, rng, world)
        elif role == "guard":
            self._behave_guard(dt, width, height, rng, world)
        else:
            super().step(dt, width, height, rng)
