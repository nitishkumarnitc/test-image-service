#!/usr/bin/env bash
set -euo pipefail
TARGET="${WAIT_FOR_URL:-http://localstack:4566/health}"
TIMEOUT="${WAIT_TIMEOUT_SEC:-60}"
n=0
echo "Waiting for $TARGET..."
until curl -fsS "$TARGET" >/dev/null 2>&1; do
  n=$((n+1))
  if [ "$n" -ge "$TIMEOUT" ]; then
    echo "Timed out waiting for $TARGET" >&2
    exit 1
  fi
  sleep 1
done
echo "$TARGET is available."
