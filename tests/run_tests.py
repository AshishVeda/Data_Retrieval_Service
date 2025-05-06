#!/usr/bin/env python3
import unittest
import sys
import os

# Add parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create a test loader
loader = unittest.TestLoader()

# Discover all tests in the tests directory
test_suite = loader.discover(os.path.dirname(__file__))

# Create a test runner and run the tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(test_suite)

# Exit with non-zero code if tests failed
sys.exit(not result.wasSuccessful()) 