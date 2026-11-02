from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from importlib import metadata
from typing import Any


def _ver(pkg: str) -> str | None:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def host_report() -> dict[str, Any]:
    xcode = shutil.which("xcode-select")
    dev_dir = None
    if xcode:
        try:
            dev_dir = subprocess.run([xcode, "-p"], capture_output=True, text=True, timeout=5).stdout.strip() or None
        except Exception:
            pass
    return {
        "os": platform.platform(), "machine": platform.machine(), "python": sys.version.split()[0],
        "pymobiledevice3": _ver("pymobiledevice3"), "fastapi": _ver("fastapi"),
        "developer_dir": dev_dir,
        "full_xcode": bool(dev_dir and "Xcode" in dev_dir),
        "root": __import__("os").geteuid() == 0,
    }
