#!/bin/sh
set -eu

PORT="${PORT:-10000}"
export PORT
PYTHONPATH="/app"
export PYTHONPATH

render_nginx_config() {
    envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
}

if [ "${1:-}" = "nginx-test" ]; then
    render_nginx_config
    exec nginx -t
fi

render_nginx_config
uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level info &
exec nginx -g "daemon off;"
