"""Restoration verification. The backend can only prove the *command* was accepted; whether the phone's real
GPS is back must be observed on the phone (Location Probe). This module compares a Probe reading with the
last simulated target."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ProbeReading:
    latitude: float
    longitude: float
    is_simulated_by_software: bool | None   # None: OS did not provide source information
    age_seconds: float                      # how old the fix is


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def verify_restore(reading: ProbeReading, previous_target: tuple[float, float] | None,
                   max_age_s: float = 30.0) -> dict[str, Any]:
    if reading.age_seconds > max_age_s:
        return {"verified": False, "reason": "stale_reading",
                "message": f"The reading is {reading.age_seconds:.0f}s old; wait for a fresh fix in Location Probe."}
    if reading.is_simulated_by_software is True:
        return {"verified": False, "reason": "still_simulated",
                "message": "Core Location still reports a software-simulated location."}
    near_target = previous_target is not None and _km(previous_target, (reading.latitude, reading.longitude)) < 0.2
    if reading.is_simulated_by_software is None:
        if near_target:
            return {"verified": False, "reason": "inconclusive_near_target",
                    "message": "No source info available and the fix is still at the old target."}
        return {"verified": False, "reason": "no_source_info",
                "message": "iOS gave no source information; the location moved away from the target but "
                           "this alone is not proof. Compare against a known real position."}
    return {"verified": True, "reason": "not_simulated",
            "message": "Core Location reports the fix is not software-simulated."}
