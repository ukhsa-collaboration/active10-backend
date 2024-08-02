#!/bin/bash

set -e

echo "Waiting for MySQL to be ready..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done


echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI application..."
uvicorn main:app --host 0.0.0.0 --port 8000
