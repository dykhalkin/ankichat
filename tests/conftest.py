"""
Configuration for pytest and shared fixtures.
"""

import os
import sys
import pytest

# Add pytest-asyncio plugin
pytest_plugins = ["pytest_asyncio"]

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variable for testing
os.environ['TELEGRAM_TOKEN'] = 'test_token'
os.environ['DEBUG_MODE'] = 'True'