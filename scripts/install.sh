#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=$(command -v python3.12 || command -v python3.13 || true)
[ -n "$PY" ] || { echo "Python 3.12+ required"; exit 1; }
"$PY" -m venv .venv
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -r requirements.lock.txt
(cd frontend && npm install && npm run build)
echo "Installed. Run ./scripts/run.sh"
