#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for MojoGOAT API tests
"""

import unittest
import sys
sys.path.append("/xpal-src/mojogoat")

from test_api import MojoGoatAPITestCase
from test_api_crud import MojoGoatAPICRUDTestCase

def run_tests():
    """Run all API tests"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(MojoGoatAPITestCase))
    suite.addTest(unittest.makeSuite(MojoGoatAPICRUDTestCase))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)

if __name__ == '__main__':
    result = run_tests()
    sys.exit(not result.wasSuccessful())