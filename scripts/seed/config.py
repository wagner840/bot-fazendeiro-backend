import sys
import os
import re

# Add root directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import supabase
from logging_config import logger

BASE_DOWNTOWN_ID = 1


def generate_code(name: str, suffix: str = "_dt") -> str:
    """Generate a code from a product name."""
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    clean = re.sub(r'_+', '_', clean).strip('_')
    return f"{clean[:40]}{suffix}"
