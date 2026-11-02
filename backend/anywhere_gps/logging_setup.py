"""Structured (JSON-lines) local logging and crash reports."""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import time
import traceback

from .config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {"ts": round(record.created, 3), "level": record.levelname, "logger": record.name,
             "msg": record.getMessage()}
        d.update(getattr(record, "ctx", {}) or {})
        if record.exc_info:
            d["exc"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(d, default=str)


def setup_logging(settings: Settings) -> None:
    settings.ensure_dirs()
    root = logging.getLogger("anywhere_gps")
    root.setLevel(logging.INFO)
    if any(getattr(h, "_agps", False) for h in root.handlers):
        return
    fh = logging.handlers.RotatingFileHandler(settings.home / "logs" / "backend.jsonl",
                                              maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(JsonFormatter())
    fh._agps = True  # type: ignore[attr-defined]
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(fh)
    root.addHandler(sh)


def write_crash_report(settings: Settings, exc: BaseException, where: str) -> str:
    settings.ensure_dirs()
    path = settings.home / "crash" / f"crash-{int(time.time() * 1000)}.json"
    path.write_text(json.dumps({
        "where": where, "type": type(exc).__name__, "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        "python": sys.version,
    }, indent=2))
    logging.getLogger("anywhere_gps").error("crash report written: %s", path)
    return str(path)
