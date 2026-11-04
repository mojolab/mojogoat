# MojoGOAT API Postman Tests

This directory contains Postman tests for the MojoGOAT API. These tests cover all the API endpoints and operations, including goat management, node operations, and relationship operations.

## Files

- `MojoGOAT_API_Tests.postman_collection.json`: The Postman collection containing all the API tests
- `MojoGOAT_API_Environment.postman_environment.json`: The Postman environment with variables used in the tests
- `prepare_test_env.sh`: A script to prepare the test environment

## Test Setup

1. Run the `prepare_test_env.sh` script to create the necessary test directories:

```bash
./prepare_test_env.sh
```

2. Start the MojoGOAT API with the test registry:

```bash
cd /xpal-src/arjunvenkatraman/mojogoat
./run_mojogoat_api.sh -r /tmp/mojogoat_test_data/registry.json -d
```

## Running the Tests in Postman

1. Import the collection and environment into Postman.
2. Select the "MojoGOAT API Environment" in Postman.
3. Run the collection in order from the beginning.

The tests are designed to be run in sequence, as they depend on each other. The collection is organized into the following folders:

- **Goat Management**: Tests for creating and listing goats
- **Node Operations**: Tests for node CRUD operations
- **Relationship Operations**: Tests for relationship operations
- **Goat-Specific Operations**: Tests for goat-specific operations like getting composition and taxonomy
- **Cleanup**: Tests for cleaning up test data

## Test Data Flow

1. The tests create goats of different types (text, memory).
2. They then create nodes and relationships on the goat named by the `{{goat}}` variable via `/api/goats/{{goat}}/...` (API v2, ADR-016; there is no active goat).
3. The tests verify that all CRUD operations work correctly.
4. Finally, they clean up the test data by deleting the relationships and nodes.

## Environment Variables

The tests use the following environment variables:

- `baseUrl`: The base URL of the API (default: http://localhost:5000)
- `testDataPath`: The path to the test data directory (default: /tmp/mojogoat_test_data)
- `goat`: The name of the goat all data requests are scoped to (default `test_text_goat`)
- `testNodeId1`: The ID of the first test node (set during tests)
- `testNodeId2`: The ID of the second test node (set during tests)
- `testRelationshipId`: The ID of the test relationship (set during tests)

## Test Assertions

Each test includes assertions to verify that:

1. The API returns the correct status code (e.g., 200 for successful GET, 201 for successful creation)
2. The response data contains the expected information
3. The API operations have the expected effect on the data