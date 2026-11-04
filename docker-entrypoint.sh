#!/bin/sh
set -eu

PORT="${PORT:-8080}"
export PYTHONPATH="/app"

# Render and other hosts inject PORT; nginx template listens on 80 internally,
# docker-compose maps host port to container 80.
uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level info &
exec nginx -g "daemon off;"
