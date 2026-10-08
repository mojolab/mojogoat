#!/bin/bash
# Run the MojoGOAT API CLI tests
# This script sets up the environment and runs the API CLI tests

set -e

# Default values
API_URL="http://localhost:5000"
TEST_DATA_PATH="/tmp/mojogoat_cli_test"
KEEP_DATA=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --url)
      API_URL="$2"
      shift 2
      ;;
    --test-data-path)
      TEST_DATA_PATH="$2"
      shift 2
      ;;
    --keep-data)
      KEEP_DATA=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --url URL               Base URL of the MojoGOAT API (default: http://localhost:5000)"
      echo "  --test-data-path PATH   Path to store test data (default: /tmp/mojogoat_cli_test)"
      echo "  --keep-data             Keep test data after tests"
      echo "  --help                  Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run '$0 --help' for usage information"
      exit 1
      ;;
  esac
done

echo "===== MojoGOAT API CLI Tests ====="
echo "API URL:         $API_URL"
echo "Test Data Path:  $TEST_DATA_PATH"
echo "Keep Data:       $KEEP_DATA"
echo "==============================="

# Ensure the API server is running
if ! curl -s "$API_URL/api/registry" > /dev/null; then
  echo "ERROR: MojoGOAT API server is not running at $API_URL"
  echo "Start the server with: python mojogoatapi.py"
  exit 1
fi

# Run the API CLI tests
CMD="python test_api_cli.py --url $API_URL --test-data-path $TEST_DATA_PATH"
if [ "$KEEP_DATA" = true ]; then
  CMD="$CMD --keep-data"
fi

echo "Running: $CMD"
echo "==============================="
$CMD

# Exit with the same status as the test script
exit $?