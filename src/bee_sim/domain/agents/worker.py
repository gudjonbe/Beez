from __future__ import annotations
from typing import Optional, Any, Deque, Tuple
from collections import deque
import math
from .bee import Bee

class WorkerBee(Bee):
    """
    Worker with multi-visit foraging + lightweight recruitment.

    Trip: wander → (maybe adopt advert) → to_flower → collect → chain → to_hive → deposit(+advertise) → wander
    """

    # Movement
    SPEED_MIN = 40.0
    SPEED_MAX = 120.0
    TURN_NOISE = 0.35
    RESPAWN_SPEED = 60.0

    # Foraging
    VISIT_QUANTA = 0.8              # nectar per visit attempt
    AVOID_MEMORY = 16               # recently visited / empty flowers to avoid
    ARRIVAL_RADIUS = 10.0           # distance to count as "arrived" at a flower
    SEEK_TIMEOUT = 5.0              # seconds before giving up on a target flower

    # Recruitment
    RECRUIT_INTERVAL = 2.0          # seconds between dance-floor samples while wandering
    ADVERTISE_MIN = 0.2             # min sip to advertise last spot
    ADVERTISE_TTL = 25.0            # seconds an advert remains

    def __init__(self, id: int, x: float, y: float, vx: float, vy: float):
        super().__init__(id, x, y, vx, vy)
        self.state: str = "wander"
        self.target_flower_id: Optional[int] = None
        self.carry: float = 0.0
        self.capacity: float = 3.0
        self._avoid: Deque[int] = deque(maxlen=self.AVOID_MEMORY)

        # recruitment memory
        self._recruit_timer: float = 0.0
        self._last_flower_xy: Optional[Tuple[float, float]] = None
        self._last_take: float = 0.0

        # seeking bookkeeping
        self._seek_timer: float = 0.0

    # --- helpers ------------------------------------------------------------

    def _go_towards(self, x: float, y: float, dt: float, speed_scale: float = 0.6):
        dx, dy = (x - self.x), (y - self.y)
        angle = math.atan2(dy, dx)
        speed = (self.SPEED_MIN + self.SPEED_MAX) * speed_scale
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def _reserve_near(self, world, x: float, y: float) -> Optional[int]:
        """Try to reserve the nearest available flower near (x,y); return id or None."""
        f = world.flowers.reserve_nearest(x, y, set(self._avoid))
        return f.id if f else None

    # --- main step ----------------------------------------------------------

    def step(self, dt: float, width: int, height: int, rng, world: Any | None = None) -> None:
        if world is None:
            # fallback motion (random-walk + bounce)
            return super().step(dt, width, height, rng)

        # ------------------------- WANDER -----------------------------------
        if self.state == "wander":
            # periodically consider adopting a dance-floor advert
            self._recruit_timer -= dt
            if (self._recruit_timer <= 0.0 and
                self.carry + 1e-6 < self.capacity and
                world.flowers.remaining() > 0):
                self._recruit_timer = self.RECRUIT_INTERVAL

                # 1) try advert target if available
                target = getattr(world, "comms", None).sample() if hasattr(world, "comms") else None
                picked_id = None
                if target is not None:
                    tx, ty = target
                    picked_id = self._reserve_near(world, tx, ty)

                # 2) fallback: reserve near current position
                if picked_id is None:
                    picked_id = self._reserve_near(world, self.x, self.y)

                if picked_id is not None:
                    self.target_flower_id = picked_id
                    self._seek_timer = 0.0
                    self.state = "to_flower"
                    return

            # otherwise, random wander with bounce
            super().step(dt, width, height, rng)

        # ------------------------- TO_FLOWER --------------------------------
        elif self.state == "to_flower":
            f = world.get_flower(self.target_flower_id) if self.target_flower_id else None
            if not f or not f.available:
                # target vanished or depleted before arrival: release & reset
                if self.target_flower_id is not None:
                    world.flowers.release_reservation(self.target_flower_id)
                self.target_flower_id = None
                self.state = "wander"
                return

            self._seek_timer += dt
            if self._seek_timer > self.SEEK_TIMEOUT:
                # failed to reach in time -> give up
                world.flowers.release_reservation(self.target_flower_id)
                self.target_flower_id = None
                self.state = "wander"
                return

            dist = math.hypot(f.x - self.x, f.y - self.y)
            if dist < self.ARRIVAL_RADIUS:
                # attempt to collect
                need = max(0.0, self.capacity - self.carry)
                got = world.flowers.collect_from(f.id, amount=min(self.VISIT_QUANTA, need))
                self._last_take = got
                self._last_flower_xy = (f.x, f.y)  # remember for potential advert
                if got > 0.0:
                    self.carry += got
                    self._avoid.append(f.id)

                # If nothing was collected, don't go home; resume searching.
                if got <= 1e-6:
                    self.target_flower_id = None
                    self.state = "wander"
                    return

                # Chain another flower if capacity remains
                if (self.carry + 1e-6) < self.capacity and world.flowers.remaining() > 0:
                    # prefer near our current position for chaining
                    nf = world.flowers.reserve_nearest(self.x, self.y, set(self._avoid))
                    if nf:
                        self.target_flower_id = nf.id
                        self._seek_timer = 0.0
                        self.state = "to_flower"
                        return

                # Otherwise head to hive
                self.target_flower_id = None
                self.state = "to_hive"
            else:
                self._go_towards(f.x, f.y, dt)

        # ------------------------- TO_HIVE ----------------------------------
        elif self.state == "to_hive":
            hx, hy = world.hive
            dist = math.hypot(hx - self.x, hy - self.y)
            if dist < (world.hive_radius + 10.0):
                # deposit nectar
                world.deposit(self.carry)

                # waggle-like advert if last sip worthwhile
                if self._last_flower_xy and self._last_take >= self.ADVERTISE_MIN and hasattr(world, "comms"):
                    strength = max(0.2, min(2.0, self._last_take / max(1e-6, self.VISIT_QUANTA)))
                    world.comms.advertise(self._last_flower_xy[0], self._last_flower_xy[1],
                                          strength=strength, ttl=self.ADVERTISE_TTL)

                # reset trip memory
                self.carry = 0.0
                self._last_flower_xy = None
                self._last_take = 0.0
                self.state = "wander"
            else:
                self._go_towards(hx, hy, dt)

        # ------------------------- UNKNOWN ----------------------------------
        else:
            super().step(dt, width, height, rng)

