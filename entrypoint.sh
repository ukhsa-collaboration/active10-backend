#!/usr/bin/env bash

set -e

mode="${1:-prod}"
: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:=5432}"
RELOAD_DIR="${RELOAD_DIR:-/app}"

reload_flags=()
if [[ "$mode" == "dev" ]]; then
  reload_flags=(
    --reload
    --reload-dir "$RELOAD_DIR"
    --reload-include "*.py"
    --reload-include "*.jinja2"
    --reload-exclude ".git/*"
    --reload-exclude ".venv/*"
    --reload-exclude "__pycache__/*"
  )
fi

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
if command -v pg_isready >/dev/null 2>&1; then
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do sleep 1; done
else
  until nc -z "$DB_HOST" "$DB_PORT"; do sleep 1; done
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI (${mode})..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  "${reload_flags[@]}"
