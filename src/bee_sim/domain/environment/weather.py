from __future__ import annotations
from dataclasses import dataclass
import math
import random

@dataclass
class WeatherSnapshot:
    tod: float              # time of day in [0..1)
    nectar: float           # nectar flow index [0..1]
    rain: bool              # raining closes foraging
    open: bool              # foraging open/closed
    mode: str               # "auto" or "manual"

class Weather:
    """
    Very simple weather/flow model:
      - 'tod' (time-of-day) advances continuously (one day ~ 10 real minutes by default).
      - nectar flow is high around mid-day, low at night (auto mode) or set manually.
      - 'rain' closes foraging even if flow is good.
    """
    def __init__(self, rng: random.Random, day_length_s: float = 600.0):
        self.rng = rng
        self.day_len = max(60.0, float(day_length_s))
        self._t = 0.0

        # Mode & state
        self.mode = "auto"        # "auto" | "manual"
        self._manual_flow = 0.7   # used when mode == "manual"
        self.rain = False

        # Cached outputs
        self._nectar = 0.7
        self._open = True

    # --- controls ----------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        if mode in ("auto", "manual"):
            self.mode = mode

    def set_flow(self, val) -> None:
        """
        Accepts either a string ("good"/"dearth") or a numeric in [0..1].
        Only used in manual mode.
        """
        if isinstance(val, str):
            v = 0.8 if val.lower() in ("good", "high") else 0.2
        else:
            try:
                v = float(val)
            except Exception:
                return
        self._manual_flow = max(0.0, min(1.0, v))

    def set_rain(self, raining: bool) -> None:
        self.rain = bool(raining)

    # --- stepping ----------------------------------------------------------
    def step(self, dt: float) -> None:
        if dt <= 0.0:
            return
        self._t = (self._t + dt) % self.day_len
        tod = self._t / self.day_len  # [0,1)

        # Diurnal flow profile: bell-like around midday
        if self.mode == "auto":
            # Map tod to angle [0..2*pi); peak at midday (pi)
            ang = (tod * 2.0 * math.pi)
            # Daylight factor: high during the middle of the day
            daylight = 0.5 * (1.0 - math.cos(ang))  # 0 at midnight, 1 at midday
            nectar = 0.15 + 0.85 * daylight
        else:
            nectar = self._manual_flow

        # Foraging open if not raining and "some daylight"
        open_flag = (not self.rain) and (tod > 0.08 and tod < 0.92)  # ~ sunrise..sunset

        # Cache
        self._nectar = max(0.0, min(1.0, nectar))
        self._open = bool(open_flag)

    # --- outputs -----------------------------------------------------------
    @property
    def tod(self) -> float:
        return self._t / self.day_len

    @property
    def nectar_index(self) -> float:
        return self._nectar

    @property
    def foraging_open(self) -> bool:
        return self._open

    def snapshot(self) -> WeatherSnapshot:
        return WeatherSnapshot(
            tod=self.tod, nectar=self.nectar_index, rain=self.rain,
            open=self.foraging_open, mode=self.mode
        )

