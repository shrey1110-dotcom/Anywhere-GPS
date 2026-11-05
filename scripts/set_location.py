#!/usr/bin/env python3
"""Hold a simulated location until Ctrl+C, then restore real GPS.

  scripts/set_location.py 40.758 -73.9855
  scripts/set_location.py --search "Eiffel Tower"
Stop the Anywhere GPS server first (only one connection per phone). The Mac must stay on and connected.
"""
import argparse
import asyncio
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from anywhere_gps.app import default_services  # noqa: E402
from anywhere_gps.config import Settings  # noqa: E402
from anywhere_gps.errors import AnywhereGpsError  # noqa: E402
from anywhere_gps.geocode import Geocoder  # noqa: E402
from anywhere_gps.session_manager import SessionManager  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lat", nargs="?", type=float)
    ap.add_argument("lon", nargs="?", type=float)
    ap.add_argument("--search")
    ap.add_argument("--udid")
    a = ap.parse_args()
    settings = Settings()
    if a.search:
        res = await Geocoder(settings).search(a.search)
        if not res:
            print("No results for that search."); return 2
        a.lat, a.lon = res[0]["latitude"], res[0]["longitude"]; print("Using:", res[0]["name"])
    if a.lat is None or a.lon is None:
        ap.error("give LAT LON or --search")
    mgr = SessionManager(default_services(settings)[0], op_timeout=settings.op_timeout)
    try:
        await mgr.set_location(a.udid, a.lat, a.lon)
    except AnywhereGpsError as e:
        print(f"{e.message}\n{e.hint}"); return 1
    print(f"Simulating {a.lat}, {a.lon}. Ctrl+C to restore real GPS.")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, stop.set)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), 2)
        except asyncio.TimeoutError:
            st = mgr.all_status()[0]
            if st["state"] != "active":
                print("Connection lost - simulation is no longer active:", st["error"]); return 3
    await mgr.shutdown()
    print("Restored (command sent). Confirm in Maps.")
    return 0


sys.exit(asyncio.run(main()))
