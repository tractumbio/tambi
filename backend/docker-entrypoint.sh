#!/bin/sh
set -e

# Apply database migrations, then start the API. DATABASE_URL must be set in the
# container environment (Azure Container App secret / app setting).
echo "[entrypoint] running migrations…"
alembic upgrade head

echo "[entrypoint] starting API on :${PORT:-8000}…"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
