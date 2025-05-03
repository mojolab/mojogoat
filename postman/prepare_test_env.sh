#!/bin/bash

# Create test data directory
TEST_DATA_DIR="/tmp/mojogoat_test_data"
mkdir -p "$TEST_DATA_DIR/goats/test_text_goat/nodes"
mkdir -p "$TEST_DATA_DIR/goats/test_text_goat/snapshots"
mkdir -p "$TEST_DATA_DIR/databases"
touch "$TEST_DATA_DIR/goats/test_text_goat/newgrass.gq"
touch "$TEST_DATA_DIR/goats/test_text_goat/goatrels.gq"

# Create registry directory
mkdir -p "$TEST_DATA_DIR"

echo "Test environment prepared at $TEST_DATA_DIR"
echo ""
echo "To run the MojoGOAT API with the test registry:"
echo "./run_mojogoat_api.sh -r $TEST_DATA_DIR/registry.json -d"
echo ""
echo "In Postman:"
echo "1. Import the collection from: /xpal-src/mojogoat/postman/MojoGOAT_API_Tests.postman_collection.json"
echo "2. Import the environment from: /xpal-src/mojogoat/postman/MojoGOAT_API_Environment.postman_environment.json"
echo "3. Select the 'MojoGOAT API Environment'"
echo "4. Run the collection from the beginning"