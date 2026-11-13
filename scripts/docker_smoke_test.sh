#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${SMOKE_IMAGE:-kwizzle-landing-smoke}"
HOST_PORT="${SMOKE_HOST_PORT:-18080}"
CONTAINER_PORT="${PORT:-10000}"

cd "$ROOT"

echo "==> docker build"
docker build -t "$IMAGE" .

echo "==> nginx -t in image"
docker run --rm "$IMAGE" /docker-entrypoint.sh nginx-test

cid="$(docker run -d -e PORT="$CONTAINER_PORT" -p "${HOST_PORT}:${CONTAINER_PORT}" "$IMAGE")"
cleanup() { docker rm -f "$cid" >/dev/null 2>&1 || true; }
trap cleanup EXIT

base="http://127.0.0.1:${HOST_PORT}"
for _ in $(seq 1 30); do
  if curl -sf "${base}/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo "==> smoke: /health (local)"
curl -sf "${base}/health" | grep -q healthy

echo "==> smoke: /.well-known/x402 (JSON)"
body="$(curl -sf "${base}/.well-known/x402")"
echo "$body" | python3 -c 'import json,sys; json.load(sys.stdin)'

echo "==> smoke: /openapi.json (JSON)"
curl -sf "${base}/openapi.json" | python3 -c 'import json,sys; json.load(sys.stdin)'

echo "==> smoke: /us/cities (JSON)"
curl -sf "${base}/us/cities" | python3 -c 'import json,sys; json.load(sys.stdin)'

echo "==> smoke: /us/mn/property-check (402)"
code="$(curl -s -o /dev/null -w '%{http_code}' "${base}/us/mn/property-check")"
test "$code" = "402"

echo "==> smoke: POST /mcp/mcp tools/list (JSON-RPC)"
curl -sf -X POST "${base}/mcp/mcp" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert "result" in d or "error" in d'

echo "==> smoke: / (landing HTML)"
curl -sf "${base}/" | grep -qi '<html'

echo "All smoke checks passed."
