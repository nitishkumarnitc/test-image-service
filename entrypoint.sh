#!/usr/bin/env bash
set -euo pipefail

RUN_TESTS="${RUN_TESTS:-0}"
AWS_ENDPOINT="${AWS_ENDPOINT_URL:-http://localstack:4566}"
WAIT_TIMEOUT="${WAIT_TIMEOUT_SEC:-60}"

wait_for_endpoint() {
  local url="$1"
  local t=0
  echo "Waiting for $url (timeout ${WAIT_TIMEOUT}s)..."
  until curl -fsS "$url" >/dev/null 2>&1; do
    t=$((t+1))
    if [ "$t" -ge "$WAIT_TIMEOUT" ]; then
      echo "Timed out waiting for $url" >&2
      return 1
    fi
    sleep 1
  done
  echo "$url is reachable"
  return 0
}

if [ "${RUN_TESTS}" = "1" ] || [ "${RUN_TESTS}" = "true" ] || [ "${RUN_TESTS}" = "True" ]; then
  export PYTHONPATH="/app:${PYTHONPATH:-}"

  if [ -n "${AWS_ENDPOINT:-}" ]; then
    HEALTH_URL="${AWS_ENDPOINT%/}/health"
    if ! wait_for_endpoint "$HEALTH_URL"; then
      wait_for_endpoint "${AWS_ENDPOINT%/}" || echo "Proceeding to run tests (LocalStack unreachable)."
    fi
  fi

  echo "Running pytest with live logging..."
  PYTEST_ARGS="${PYTEST_ARGS:--vv --maxfail=1 --log-cli-level=INFO -r a}"
  pytest $PYTEST_ARGS -q
  RC=$?
  echo "pytest finished with exit code: $RC"
  exit $RC
fi

exec "$@"
