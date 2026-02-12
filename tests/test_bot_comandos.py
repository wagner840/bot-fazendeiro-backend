# Re-export for backward compatibility
# Can be run directly: python -m pytest tests/test_bot_comandos.py
import asyncio
import sys
import os

# Ensure tests/ is on the path for test_bot package
sys.path.insert(0, os.path.dirname(__file__))

from test_bot.runner import run_all_tests, main

if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
