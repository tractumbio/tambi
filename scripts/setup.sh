#!/usr/bin/env bash
# One-shot local environment setup for macOS / Linux / WSL.
# See docs/GETTING_STARTED.md for what each step does and why.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Checking prerequisites"
for cmd in git python3 node docker; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: '$cmd' is not installed or not on PATH. See docs/GETTING_STARTED.md." >&2
    exit 1
  fi
done

echo "==> Setting up .env"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it if you need non-default values."
else
  echo ".env already exists, leaving it untouched."
fi

echo "==> Setting up backend virtual environment"
cd "$ROOT_DIR/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
deactivate

echo "==> Installing frontend dependencies"
cd "$ROOT_DIR/frontend"
npm install

echo ""
echo "Setup complete. Next steps:"
echo "  1. Start the backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "  2. Start the frontend: cd frontend && npm run dev"
echo "  3. (Optional) Pull an Ollama model: ollama pull llama3.1 && ollama serve"
echo "See docs/GETTING_STARTED.md for details, or run scripts/start-dev.sh to start backend+frontend together."
