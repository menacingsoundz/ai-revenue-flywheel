#!/bin/bash
# Start the AI Revenue Flywheel locally.
cd "$(dirname "$0")"
.venv/bin/python -m app.seed
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
