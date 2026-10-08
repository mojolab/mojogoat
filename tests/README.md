# MojoGOAT Test Suite

This directory contains test suites for various components of the MojoGOAT application.

## API Testing Tools

### API Unit Tests

These tests use the Python `unittest` framework to test API functionality directly:

```bash
# Run all API tests
python run_api_tests.py
```

This runs the unit tests defined in:
- `test_api.py` - Tests for goat management API endpoints
- `test_api_crud.py` - Tests for CRUD operations API endpoints

### API CLI Tests

The CLI test script provides a command-line tool for testing all API endpoints:

```bash
# Run the API CLI tests with default settings
./run_api_cli_tests.sh

# Run with custom settings
./run_api_cli_tests.sh --url http://localhost:5000 --test-data-path /path/to/test/data --keep-data
```

The CLI test script (`test_api_cli.py`) performs the following tests:

1. **Goat Management**
   - Registry operations
   - Goat creation (text and MongoDB+PostgreSQL)
   - Goat selection

2. **Node Operations**
   - Create nodes with different labels and properties
   - Retrieve nodes by ID and label
   - Update node properties
   - Delete nodes

3. **Relationship Operations**
   - Create relationships between nodes
   - Retrieve relationships by ID, source, target, and story
   - Delete relationships

4. **Goat-Specific Operations**
   - Get composition (count of nodes by label)
   - Get taxonomy (count of relationships by story)
   - Dump relationships to a file

## MongoDB+PostgreSQL Tests

These tests validate the MongoDB+PostgreSQL goat base:

```bash
# Run with default settings
python run_mongodbpostgres_tests.py

# Run with custom config file
python run_mongodbpostgres_tests.py --config testdata/mongodbpostgres_config.json --clean
```

The MongoDB+PostgreSQL tests include:
- `test_mongodbpostgres_nodes.py` - Tests for node operations
- `test_mongodbpostgres_relationships.py` - Tests for relationship operations
- `test_mongodbpostgres_queries.py` - Tests for complex queries

## Configuration

### API CLI Test Configuration

The API CLI tests can be configured with the following options:

- `--url URL` - Base URL of the MojoGOAT API (default: http://localhost:5000)
- `--test-data-path PATH` - Path to store test data (default: /tmp/mojogoat_cli_test)
- `--keep-data` - Keep test data after tests (default: false)

### MongoDB+PostgreSQL Test Configuration

The MongoDB+PostgreSQL tests require a configuration file with the following format:

```json
{
  "mongodb_uri": "mongodb://localhost/mojogoat_test",
  "postgres_uri": "sqlite:///test_relationships.db",
  "debug": true, 
  "testing": true
}
```

## Running all Tests

To run all tests in sequence:

```bash
# First start the API server
cd /xpal-src/mojogoat
python mojogoatapi.py &

# Run the MongoDB+PostgreSQL tests
cd test
python run_mongodbpostgres_tests.py

# Run the API unit tests
python run_api_tests.py

# Run the API CLI tests
./run_api_cli_tests.sh
```

## Test Data Cleanup

By default, test data is cleaned up after tests run. For debugging, you can keep the data:

- For API CLI tests: Use the `--keep-data` flag
- For MongoDB+PostgreSQL tests: Omit the `--clean` flag