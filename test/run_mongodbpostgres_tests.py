#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for MongoDB+Postgres tests
"""

import os
import sys
import unittest
import argparse
import json
import tempfile
import sys
sys.path.append("/xpal-src/mojogoat")
# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules (only use basic test modules)
from test_mongodbpostgres_nodes import TestMongoDBNodes
from test_mongodbpostgres_relationships import TestMongoDBPostgresRelationships

def run_tests(config_path):
    """Run all MongoDB+Postgres tests
    
    Args:
        config_path: Path to database configuration JSON file
        
    Returns:
        Test result
    """
    # Set environment variable for tests to use
    os.environ['MOJOGOAT_CONFIG'] = config_path
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests to the suite (only basic tests)
    suite.addTests(loader.loadTestsFromTestCase(TestMongoDBNodes))
    suite.addTests(loader.loadTestsFromTestCase(TestMongoDBPostgresRelationships))
    
    # Initialize test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = runner.run(suite)
    return result

def create_default_config():
    """Create a default config file if none is provided
    
    Returns:
        Path to created config file
    """
    default_config = {
        "mongodb_uri": "mongodb://localhost/mojogoat_test",
        "postgres_uri": "postgresql://postgres:postgres@localhost:5432/xetrapal"
    }
    
    # Create a temporary file
    _, config_path = tempfile.mkstemp(suffix='.json')
    
    # Write default config to file
    with open(config_path, 'w') as f:
        json.dump(default_config, f)
    
    return config_path

def clean_up_test_data():
    """Clean up test data after tests"""
    # This could be expanded to do more thorough cleanup if needed
    pass

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run MongoDB+Postgres tests")
    parser.add_argument(
        "--config", 
        help="Path to the database configuration JSON file", 
        default=None
    )
    parser.add_argument(
        "--clean",
        help="Clean up test data after tests",
        action="store_true"
    )
    args = parser.parse_args()
    
    # Use provided config or create default
    config_path = args.config
    config_is_temp = False
    
    if not config_path:
        config_path = create_default_config()
        config_is_temp = True
    
    # Run tests
    print(f"Running tests with config: {config_path}")
    result = run_tests(config_path)
    
    # Clean up
    if args.clean:
        clean_up_test_data()
    
    # Remove temporary config if created
    if config_is_temp and os.path.exists(config_path):
        os.unlink(config_path)
    
    # Exit with appropriate status code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())