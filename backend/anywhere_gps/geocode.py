"""Nominatim geocoding with a hard 1 req/s limit, a User-Agent, and an in-memory cache."""
from __future__ import annotations

import asyncio
import time

import httpx

from .config import Settings
from .errors import GeocodeFailed, RateLimited


class Geocoder:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.s = settings
        self.client = client or httpx.AsyncClient(timeout=8, headers={"User-Agent": "AnywhereGPS/0.1 (local app)"})
        self._last = 0.0
        self._lock = asyncio.Lock()
        self._cache: dict[str, list[dict]] = {}

    async def search(self, q: str) -> list[dict]:
        q = q.strip()
        if len(q) < 2:
            return []
        if q.lower() in self._cache:
            return self._cache[q.lower()]
        async with self._lock:
            wait = self._last + self.s.geocode_min_interval - time.monotonic()
            if wait > 0.5:        # a burst of typing: refuse rather than queue up requests
                raise RateLimited("Searching too quickly.")
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()
            try:
                r = await self.client.get(self.s.geocode_url, params={"q": q, "format": "jsonv2", "limit": 6})
                r.raise_for_status()
                data = r.json()
            except (httpx.HTTPError, ValueError) as e:
                raise GeocodeFailed(f"Geocoding failed: {e}") from e
        out = [{"name": d["display_name"], "latitude": float(d["lat"]), "longitude": float(d["lon"])} for d in data]
        self._cache[q.lower()] = out
        return out
