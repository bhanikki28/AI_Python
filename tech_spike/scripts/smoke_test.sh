#!/usr/bin/env bash
# Build the container, start it, and check the core path over real HTTP.
# Used by `make docker-smoke` locally and by CI.
set -euo pipefail

IMAGE="${IMAGE:-pii-gate:local}"
PORT="${PORT:-18000}"
NAME="pii-gate-smoke-$$"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker build -q -t "$IMAGE" . >/dev/null
docker run -d --name "$NAME" --read-only -p "127.0.0.1:${PORT}:8000" "$IMAGE" >/dev/null

for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null && break
  sleep 1
done

fail() { echo "SMOKE FAIL: $1"; docker logs "$NAME" | tail -20; exit 1; }

health=$(curl -sf "http://127.0.0.1:${PORT}/health") || fail "health endpoint"
echo "health: $health"
echo "$health" | grep -q '"status":"ok"' || fail "service not ready"
echo "$health" | grep -q '"assistant":"disabled"' || fail "assistant should be disabled in image"

scan() {
  curl -sf -X POST "http://127.0.0.1:${PORT}/v1/scan" \
    -H 'content-type: application/json' -d "{\"text\": \"$1\"}"
}

scan "card 4111 1111 1111 1111 call 0412 345 678" | grep -q '"decision":"REDACT"' || fail "REDACT path"
scan "My TFN is 123 456 782" | grep -q '"decision":"BLOCK"' || fail "BLOCK path"
scan "The branch was closed" | grep -q '"decision":"ALLOW"' || fail "ALLOW path"
curl -sf "http://127.0.0.1:${PORT}/" | grep -q "PII Gate" || fail "UI"

if docker logs "$NAME" 2>&1 | grep -qE "4111|0412 345|123 456 782"; then
  fail "raw PII found in container logs"
fi

user=$(docker exec "$NAME" id -u)
[ "$user" != "0" ] || fail "container runs as root"

echo "SMOKE PASS: health, ALLOW/REDACT/BLOCK, UI, PII-free logs, non-root (uid $user)"
