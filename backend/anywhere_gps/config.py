from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _home() -> Path:
    return Path(os.environ.get("ANYWHERE_GPS_HOME", Path.home() / ".anywhere-gps"))


@dataclass
class Settings:
    home: Path = field(default_factory=_home)
    backend: str = field(default_factory=lambda: os.environ.get("ANYWHERE_GPS_BACKEND", "real"))
    host: str = "127.0.0.1"          # localhost only by default
    port: int = int(os.environ.get("ANYWHERE_GPS_PORT", "8765"))
    op_timeout: float = 20.0         # any single developer-service call
    connect_attempts: int = 3
    backoff_base: float = 0.5
    monitor_interval: float = 2.0
    geocode_min_interval: float = 1.1  # Nominatim usage policy: max 1 request/second
    geocode_url: str = "https://nominatim.openstreetmap.org/search"

    def ensure_dirs(self) -> None:
        for sub in ("logs", "crash"):
            (self.home / sub).mkdir(parents=True, exist_ok=True)
