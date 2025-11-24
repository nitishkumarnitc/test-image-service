#!/bin/sh
set -e

ENDPOINT=${AWS_ENDPOINT_URL:-http://localstack:4566}
RETRIES=${WAIT_RETRIES:-60}
SLEEP=${WAIT_SLEEP:-2}

i=0
echo "Waiting for LocalStack at ${ENDPOINT} (max ${RETRIES} retries)..."

until curl -sS "${ENDPOINT}/health" | grep -q '"status"' ; do
  i=$((i+1))
  if [ "$i" -ge "$RETRIES" ]; then
    echo "Timeout waiting for LocalStack at ${ENDPOINT}"
    exit 1
  fi
  sleep $SLEEP
done

echo "LocalStack reachable at ${ENDPOINT}"

# run python-based resource initializer if present
if command -v python3 >/dev/null 2>&1 && [ -f "./create_resources.py" ]; then
  echo "Running create_resources.py..."
  python3 create_resources.py || echo "create_resources.py failed but continuing"
else
  echo "create_resources.py not found or python3 missing; skipping resource creation"
fi

# exec the CMD provided by Docker (start server)
exec "$@"
