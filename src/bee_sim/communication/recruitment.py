from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import random

@dataclass
class Advert:
    """A short-lived 'dance' advertisement for a location."""
    x: float
    y: float
    strength: float   # relative weight for sampling (0..inf)
    ttl: float        # seconds to live

class RecruitmentBoard:
    """Minimal board storing waggle-like adverts.

    Foragers call advertise(x,y,strength,ttl);
    Idle workers call sample() to get a suggested (x,y);
    step(dt) decays TTL and prunes old adverts.
    """
    def __init__(self, rng: random.Random, max_ads: int = 64) -> None:
        self.rng = rng
        self.max_ads = max_ads
        self._ads: List[Advert] = []

    def step(self, dt: float) -> None:
        if dt <= 0: return
        alive: List[Advert] = []
        for ad in self._ads:
            ad.ttl -= dt
            if ad.ttl > 0:
                # gentle fade keeps newest/successful adverts more attractive
                ad.strength *= 0.999
                alive.append(ad)
        self._ads = alive

    def advertise(self, x: float, y: float, strength: float, ttl: float = 25.0) -> None:
        if strength <= 0 or ttl <= 0: return
        self._ads.append(Advert(x=x, y=y, strength=strength, ttl=ttl))
        if len(self._ads) > self.max_ads:
            self._ads = self._ads[-self.max_ads:]

    def sample(self) -> Optional[Tuple[float, float]]:
        if not self._ads: return None
        weights = [ad.strength for ad in self._ads]
        idx = self._weighted_choice(weights, self.rng)
        ad = self._ads[idx]
        return (ad.x, ad.y)

    @staticmethod
    def _weighted_choice(weights: List[float], rng: random.Random) -> int:
        total = sum(w for w in weights if w > 0)
        if total <= 0: return 0
        r = rng.uniform(0, total)
        acc = 0.0
        for i, w in enumerate(weights):
            if w <= 0: continue
            acc += w
            if r <= acc: return i
        return len(weights) - 1

    def snapshot(self) -> dict:
        return { "adverts": len(self._ads) }
