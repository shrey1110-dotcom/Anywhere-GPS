#!/usr/bin/env bash
# Launch Anywhere GPS: ./scripts/run.sh [--mock]   (UI at http://127.0.0.1:8765)
set -euo pipefail
cd "$(dirname "$0")/.."
[ "${1:-}" = "--mock" ] && export ANYWHERE_GPS_BACKEND=mock
[ -d .venv ] || ./scripts/install.sh
[ -f frontend/dist/index.html ] || (cd frontend && npm install && npm run build)
exec env PYTHONPATH=backend .venv/bin/python -m anywhere_gps.app
