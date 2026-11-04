#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for MojoGOAT API tests (goat-scoped API v2, ADR-016)
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def run_tests():
    """Run all API tests; returns the pytest exit code."""
    return pytest.main([
        os.path.join(HERE, "test_api.py"),
        os.path.join(HERE, "test_api_crud.py"),
        os.path.join(HERE, "test_api_v2.py"),
        os.path.join(HERE, "test_operations_persistence.py"),
        "-v", "-p", "no:cacheprovider",
    ])


if __name__ == '__main__':
    sys.exit(int(run_tests()))
