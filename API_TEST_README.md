# MojoGOAT API Testing Framework

This document describes the comprehensive testing framework for the MojoGOAT API.

## Overview

The MojoGOAT API testing framework consists of three main components:

1. **Unit Tests** - Python unittest framework for direct API testing
2. **CLI Test Tool** - Command-line tool for testing all API endpoints
3. **Postman Collection** - Comprehensive Postman tests for GUI-based testing

## Prerequisites

Before running the tests, ensure you have:

- Python 3.6+
- MongoDB running locally (for MongoDB+PostgreSQL tests)
- PostgreSQL or SQLite for relationship storage
- Postman (for Postman collection tests)
- Required Python packages: `flask`, `flask_sqlalchemy`, `flask_migrate`, `mongoengine`, `flask_mongoengine`, `requests`

## Running Tests

### Running All Tests

To run all test suites at once:

```bash
cd /xpal-src/mojogoat/test
./run_all_tests.sh
```

This script:
1. Starts the MojoGOAT API server if it's not already running
2. Runs the MongoDB+PostgreSQL tests
3. Runs the API unit tests
4. Runs the API CLI tests
5. Provides a summary of test results

### Running Individual Test Suites

#### Unit Tests

```bash
cd /xpal-src/mojogoat/test
python run_api_tests.py
```

#### CLI Tests

```bash
cd /xpal-src/mojogoat/test
./run_api_cli_tests.sh
```

Options:
- `--url URL` - Base URL of the MojoGOAT API (default: http://localhost:5000)
- `--test-data-path PATH` - Path to store test data (default: /tmp/mojogoat_cli_test)
- `--keep-data` - Keep test data after tests (default: false)

#### Postman Tests

1. Import the collection from `/xpal-src/mojogoat/postman/MojoGOAT_API_Tests.postman_collection.json`
2. Import the environment from `/xpal-src/mojogoat/postman/MojoGOAT_API_Environment.postman_environment.json`
3. Run the collection via the Postman UI or Newman CLI

## Test Components

### Unit Tests

Located in `/xpal-src/mojogoat/test/`:

- `test_api.py` - Tests for goat management API endpoints
- `test_api_crud.py` - Tests for CRUD operations API endpoints

### CLI Test Tool

The CLI test tool (`test_api_cli.py`) is a comprehensive script that tests all API endpoints:

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

### Postman Collection

The Postman collection (`MojoGOAT_API_Tests.postman_collection.json`) contains organized folders for testing:

1. **Registry Management**
   - Get registry path
   - Set registry path

2. **Goat Management**
   - List goats
   - Create text goat
   - Create MongoDB+PostgreSQL goat
   - Set active goat

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

Located in `/xpal-src/mojogoat/test/`:

- `test_mongodbpostgres_nodes.py` - Tests for node operations
- `test_mongodbpostgres_relationships.py` - Tests for relationship operations
- `test_mongodbpostgres_queries.py` - Tests for complex queries

## Troubleshooting

### API Server Issues

If the API server fails to start:
- Check port availability: `lsof -i :5000`
- Check MongoDB connection: `mongod --version`
- Check PostgreSQL connection (if applicable)
- Review logs: `/tmp/mojogoat_api.log`

### Testing Issues

- Ensure test dependencies are installed: `pip install -r requirements.txt`
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