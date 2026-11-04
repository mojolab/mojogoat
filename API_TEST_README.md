# MojoGOAT API Testing Framework

This document describes the comprehensive testing framework for the MojoGOAT API.

The API is goat-scoped (API v2, ADR-016; spec: `docs/api-v2-goat-scoped.md`). There is no
"active goat": every data route is `/api/goats/<goat>/...`, and the tests name their goat in
every URL. Removed v1 routes (`/api/nodes`, `/api/active-goat`, ...) return `410 Gone`.

## Overview

The MojoGOAT API testing framework consists of three main components:

1. **Unit Tests** - pytest/unittest tests that drive the Flask app with its test client
2. **CLI Test Tool** - Command-line tool for testing all API endpoints
3. **Postman Collection** - Comprehensive Postman tests for GUI-based testing

## Prerequisites

Before running the tests, ensure you have:

- Python 3.11+ and `uv` (always run through `uv run --frozen --extra dev ...`)
- MongoDB and PostgreSQL/SQLite only for the (deferred) MongoDB+PostgreSQL tests
- Postman (for Postman collection tests)
- The `requests` package (in the `dev` extra) for the CLI tests

## Running Tests

### Running All Tests

To run all test suites at once:

```bash
cd /xpal-src/arjunvenkatraman/mojogoat/tests
./run_all_tests.sh
```

This script:
1. Starts a throwaway API v2 server on port 5099 (`MOJOGOAT_TEST_PORT`) with temp registry,
   data and operations directories; it never reuses a server that is already running
2. Runs the MongoDB+PostgreSQL tests
3. Runs the API unit tests
4. Runs the API CLI tests against the throwaway server
5. Stops that server, removes the temp state and prints a summary

### Running Individual Test Suites

#### Unit Tests

```bash
cd /xpal-src/arjunvenkatraman/mojogoat
uv run --frozen --extra dev pytest tests/ -m "not integration" -q -p no:cacheprovider
```

(`tests/run_api_tests.py` runs just the API test modules through pytest.) Unit tests are fully
isolated: temp registry, temp `MOJOGOAT_OPERATIONS_DIR`, temp `mojogoatapi.DEFAULT_DATA_DIR`,
empty `mojogoatapi._goat_cache`; nothing under `/xpal-data` is touched.

#### CLI Tests

Start a throwaway v2 server first (the CLI tests create goats and switch the registry, so do
not point them at a server you use):

```bash
cd /xpal-src/arjunvenkatraman/mojogoat
MOJOGOAT_REGISTRY=/tmp/mg/reg.json MOJOGOAT_DATA=/tmp/mg/goats MOJOGOAT_OPERATIONS_DIR=/tmp/mg/ops \
  uv run --frozen --extra dev python mojogoatapi.py --port 5099
```

then:

```bash
cd /xpal-src/arjunvenkatraman/mojogoat/tests
./run_api_cli_tests.sh --url http://localhost:5099
```

Options:
- `--url URL` - Base URL of the MojoGOAT API (default: http://localhost:5000; use a throwaway server)
- `--test-data-path PATH` - Path to store test data (default: /tmp/mojogoat_cli_test)
- `--keep-data` - Keep test data after tests (default: false)

#### Postman Tests

1. Import the collection from `/xpal-src/arjunvenkatraman/mojogoat/postman/MojoGOAT_API_Tests.postman_collection.json`
2. Import the environment from `/xpal-src/arjunvenkatraman/mojogoat/postman/MojoGOAT_API_Environment.postman_environment.json`
3. Run the collection via the Postman UI or Newman CLI (the `goat` variable names the goat every data request uses)

## Test Components

### Unit Tests

Located in `/xpal-src/arjunvenkatraman/mojogoat/tests/`:

- `test_api.py` - goat management and the scoped data routes (graph, operations, compaction, import)
- `test_api_crud.py` - CRUD operations on one goat through `/api/goats/<goat>/...`
- `test_api_v2.py` - ADR-016 behaviour: goat isolation, 404 for unknown/invalid goats, 410 stubs for
  removed routes, goat-name and path validation, scoped operations, registry/cache lifecycle
- `test_operations_persistence.py` - operation persistence (operations carry a `goat`; files
  without one are skipped on reload)
- `api_support.py` - shared isolation helper

### CLI Test Tool

The CLI test tool (`test_api_cli.py`) is a comprehensive script that tests all API endpoints:

1. **Goat Management**
   - Registry operations
   - Goat creation (text and memory), `GET /api/goats/<name>`, rejection of `make_active`/`make_default`
   - API v2 contract (`api_version` in `/api/status`, `410` for removed routes)

2. **Node Operations**
   - Create nodes with different labels and properties (all under `/api/goats/<goat>/nodes`)
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

### Postman Collection

The Postman collection (`MojoGOAT_API_Tests.postman_collection.json`) contains organized folders for testing:

1. **Registry Management**
   - Get registry path
   - Set registry path

2. **Goat Management**
   - List goats
   - Create text goat
   - Create memory goat

3. **Node Operations**
   - Create nodes
   - Get nodes by ID
   - Get nodes by label
   - Update nodes
   - Delete nodes

4. **Relationship Operations**
   - Create relationships
   - Get relationships
   - Filter relationships
   - Delete relationships

5. **Goat Operations**
   - Get composition
   - Get taxonomy
   - Dump relationships

## MongoDB+PostgreSQL Tests

Located in `/xpal-src/arjunvenkatraman/mojogoat/tests/`:

- `test_mongodbpostgres_nodes.py` - Tests for node operations
- `test_mongodbpostgres_relationships.py` - Tests for relationship operations
- `test_mongodbpostgres_queries.py` - Tests for complex queries

## Troubleshooting

### API Server Issues

If the API server fails to start:
- Check port availability: `lsof -i :5000`
- Check MongoDB connection: `mongod --version`
- Check PostgreSQL connection (if applicable)
- Review the server log (`run_all_tests.sh` prints its temp path on failure)

### Testing Issues

- Ensure test dependencies are installed: `uv sync --extra dev` (never bare `pip install`)
- Check MongoDB is running: `mongo --eval "db.version()"`
- For CLI tests, verify the API server is running: `curl http://localhost:5000/api/registry`
- For mongoDB+Postgres tests, check database connection strings

## Extending Tests

### Adding New API Tests

1. Identify the API endpoint(s) to test
2. Add test methods to `test_api.py` or `test_api_crud.py` for unit tests
3. Add test methods to `test_api_cli.py` for CLI tests
4. Add request(s) to the Postman collection for GUI-based testing

### Adding New MongoDB+PostgreSQL Tests

1. Create a new test file or add test methods to existing files
2. Add the test class to `run_mongodbpostgres_tests.py`
3. Update the CLI test tool as needed