#!/bin/bash
# Run all MojoGOAT tests
# This script runs all MojoGOAT test suites in sequence

set -e

echo "===== MojoGOAT Test Suite ====="
echo "Running all tests..."
echo

# Check if API server is running
API_RUNNING=false
if curl -s http://localhost:5000/api/registry > /dev/null 2>&1; then
  API_RUNNING=true
  echo "MojoGOAT API server is already running"
else
  echo "Starting MojoGOAT API server..."
  
  # Start the API server in the background
  cd /xpal-src/mojogoat
  python mojogoatapi.py > /tmp/mojogoat_api.log 2>&1 &
  API_PID=$!
  
  # Wait for the API server to start
  MAX_WAIT=10
  WAIT_COUNT=0
  while ! curl -s http://localhost:5000/api/registry > /dev/null 2>&1; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
      echo "ERROR: API server failed to start within $MAX_WAIT seconds"
      echo "Check the log file: /tmp/mojogoat_api.log"
      exit 1
    fi
  done
  
  echo "API server started (PID: $API_PID)"
fi

# Run MongoDB+PostgreSQL tests
echo
echo "===== Running MongoDB+PostgreSQL Tests ====="
cd /xpal-src/mojogoat/test
python run_mongodbpostgres_tests.py --clean
MONGOPG_RESULT=$?

# Run API unit tests
echo
echo "===== Running API Unit Tests ====="
python run_api_tests.py
API_RESULT=$?

# Run API CLI tests
echo
echo "===== Running API CLI Tests ====="
./run_api_cli_tests.sh
CLI_RESULT=$?

# Cleanup
if [ "$API_RUNNING" = false ] && [ -n "$API_PID" ]; then
  echo
  echo "Stopping API server (PID: $API_PID)..."
  kill $API_PID
fi

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