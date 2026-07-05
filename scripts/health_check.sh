#!/usr/bin/env bash
set -Eeuo pipefail

API_URL="${1:-${API_URL:-http://127.0.0.1:${DOCSHOP_PORT:-8080}/health}}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-5}"
MAX_TIME="${MAX_TIME:-10}"
OUTPUT_FILE="${OUTPUT_FILE:-/tmp/docshop-health-response.json}"

status_code="$(curl -sS -o "$OUTPUT_FILE" -w '%{http_code}' \
  --connect-timeout "$CONNECT_TIMEOUT" \
  --max-time "$MAX_TIME" \
  "$API_URL" || true)"

if [[ "$status_code" =~ ^2[0-9][0-9]$ ]]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') health OK ${API_URL} HTTP ${status_code}"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') health FAIL ${API_URL} HTTP ${status_code}" >&2
if [[ -s "$OUTPUT_FILE" ]]; then
  head -c 1000 "$OUTPUT_FILE" >&2 || true
  echo >&2
fi
exit 1
