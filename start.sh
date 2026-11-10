#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python;
elif command -v python >/dev/null 2>&1; then PY=python;
else PY=python3; fi
"$PY" -m app.seed
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
