#!/bin/bash
# Double-click to start Anywhere GPS and open it in the browser. Close this window (or Ctrl+C) to stop and restore real GPS.
cd "$(dirname "$0")"
pkill -INT -f anywhere_gps.app 2>/dev/null; sleep 1
(sleep 3; open http://127.0.0.1:8765) &
./scripts/run.sh
