#!/usr/bin/env bash
# Start backend and frontend dev servers together. Requires scripts/setup.sh
# to have been run at least once. Press Ctrl+C to stop both.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  echo ""
  echo "Stopping dev servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Starting backend on :8000"
(
  cd "$ROOT_DIR/backend"
  source .venv/bin/activate
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "==> Starting frontend on :5173"
(
  cd "$ROOT_DIR/frontend"
  npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo "(Ollama is not started by this script — run 'ollama serve' separately if needed.)"

wait
