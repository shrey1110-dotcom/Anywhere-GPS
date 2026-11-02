from __future__ import annotations

import enum
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    from .errors import InvalidCoordinates
    import math
    for name, v, lim in (("latitude", latitude, 90.0), ("longitude", longitude, 180.0)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise InvalidCoordinates(f"{name} must be a finite number, got {v!r}.")
        if abs(v) > lim:
            raise InvalidCoordinates(f"{name} {v} is outside -{lim:g}..{lim:g}.")
    return float(latitude), float(longitude)


@dataclass
class DeviceInfo:
    udid: str
    name: str | None = None
    ios_version: str | None = None
    product_type: str | None = None
    connection: str = "USB"
    paired: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Readiness:
    udid: str
    paired: bool
    ios_supported: bool
    developer_mode: bool | None      # None = could not be determined
    image_mounted: bool | None
    ios_version: str | None = None
    problems: list[dict[str, str]] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.paired and self.ios_supported and self.developer_mode is True and self.image_mounted is True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ready"] = self.ready
        return d


class SessionState(str, enum.Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    RESTORING = "restoring"
    LOST = "lost"
    ERROR = "error"


class LocationChannel(Protocol):
    """An open developer-service connection. The simulated location lives only as long as it is open
    (see ARCHITECTURE.md; hardware confirmation pending)."""

    async def set(self, latitude: float, longitude: float) -> None: ...
    async def clear(self) -> None: ...
    async def ping(self) -> None: ...    # raises DeviceUnreachable when the link is dead
    async def close(self) -> None: ...


class DiscoveryService(Protocol):
    async def list_devices(self) -> list[DeviceInfo]: ...


class SetupService(Protocol):
    async def check(self, udid: str) -> Readiness: ...
    async def mount_image(self, udid: str) -> None: ...


class SimulatorService(Protocol):
    async def open(self, udid: str) -> LocationChannel: ...


@dataclass
class Services:
    discovery: DiscoveryService
    setup: SetupService
    simulator: SimulatorService
    kind: str  # "real" | "mock"


def now() -> float:
    return time.time()
