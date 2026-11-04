#!/bin/bash
# Run all MojoGOAT tests
# This script runs all MojoGOAT test suites in sequence

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_PY="uv run --frozen --extra dev python"

echo "===== MojoGOAT Test Suite ====="
echo "Running all tests..."
echo

# The CLI tests create goats and switch the registry, so they always run against a throwaway
# API v2 server on its own port with temp state -- never against a server you are using.
TEST_PORT="${MOJOGOAT_TEST_PORT:-5099}"
API_URL="http://localhost:$TEST_PORT"
if curl -s "$API_URL/health" > /dev/null 2>&1; then
  echo "ERROR: something is already listening on port $TEST_PORT (set MOJOGOAT_TEST_PORT)"
  exit 1
fi

TMP_STATE="$(mktemp -d)"
echo "Starting MojoGOAT API server on port $TEST_PORT (state in $TMP_STATE)..."
cd "$REPO_ROOT"
MOJOGOAT_REGISTRY="$TMP_STATE/reg.json" MOJOGOAT_DATA="$TMP_STATE/goats" \
  MOJOGOAT_OPERATIONS_DIR="$TMP_STATE/ops" \
  $UV_PY mojogoatapi.py --port "$TEST_PORT" > "$TMP_STATE/api.log" 2>&1 &
API_PID=$!

# Wait for the API server to start
MAX_WAIT=20
WAIT_COUNT=0
while ! curl -s "$API_URL/health" > /dev/null 2>&1; do
  sleep 1
  WAIT_COUNT=$((WAIT_COUNT + 1))
  if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "ERROR: API server failed to start within $MAX_WAIT seconds"
    echo "Check the log file: $TMP_STATE/api.log"
    kill $API_PID 2>/dev/null || true
    exit 1
  fi
done
echo "API server started (PID: $API_PID)"

# Run MongoDB+PostgreSQL tests
echo
echo "===== Running MongoDB+PostgreSQL Tests ====="
cd "$REPO_ROOT/tests"
set +e
$UV_PY run_mongodbpostgres_tests.py --clean
MONGOPG_RESULT=$?

# Run API unit tests
echo
echo "===== Running API Unit Tests ====="
$UV_PY run_api_tests.py
API_RESULT=$?

# Run API CLI tests
echo
echo "===== Running API CLI Tests ====="
bash ./run_api_cli_tests.sh --url "$API_URL" --test-data-path "$TMP_STATE/cli"
CLI_RESULT=$?
set -e

# Cleanup
echo
echo "Stopping API server (PID: $API_PID)..."
kill $API_PID
rm -rf "$TMP_STATE"

# Print test summary
echo
echo "===== Test Summary ====="
echo "MongoDB+PostgreSQL Tests: $([ $MONGOPG_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"
echo "API Unit Tests:           $([ $API_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"
echo "API CLI Tests:            $([ $CLI_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"

# Overall result
if [ $MONGOPG_RESULT -eq 0 ] && [ $API_RESULT -eq 0 ] && [ $CLI_RESULT -eq 0 ]; then
  echo
  echo "All tests PASSED!"
  exit 0
else
  echo
  echo "Some tests FAILED!"
  exit 1
fi