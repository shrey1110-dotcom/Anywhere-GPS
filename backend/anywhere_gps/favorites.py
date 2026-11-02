from __future__ import annotations

import json
import uuid
from pathlib import Path


class Favorites:
    def __init__(self, home: Path) -> None:
        self.path = home / "favorites.json"

    def list(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return []

    def add(self, name: str, latitude: float, longitude: float) -> dict:
        items = self.list()
        item = {"id": uuid.uuid4().hex[:12], "name": name.strip()[:80] or "Untitled",
                "latitude": latitude, "longitude": longitude}
        items.append(item)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items, indent=2))
        return item

    def remove(self, fid: str) -> bool:
        items = self.list()
        keep = [i for i in items if i["id"] != fid]
        if len(keep) == len(items):
            return False
        self.path.write_text(json.dumps(keep, indent=2))
        return True
