#!/bin/sh
set -e

echo "=== CutCost Backend Starting ==="
echo "PORT=$PORT"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo yes || echo NO)"
echo "REDIS_URL set: $([ -n "$REDIS_URL" ] && echo yes || echo NO)"
echo "ENVIRONMENT=$ENVIRONMENT"

echo "--- Running migrations ---"
alembic upgrade head || echo "WARNING: Migration failed, continuing..."

echo "--- Starting uvicorn on port ${PORT:-8000} ---"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
