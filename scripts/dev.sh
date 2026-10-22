#!/usr/bin/env bash
# Starts backend (8000) and frontend (5173) for local development on macOS/Linux/Git-Bash.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/ml"
(cd "$ROOT" && python -m uvicorn app.main:app --app-dir backend --reload --port 8000) &
(cd "$ROOT/frontend" && npm run dev) &
wait
