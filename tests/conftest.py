"""Pytest configuration for SDK tests."""

import sys
from pathlib import Path


# Add parent directory to path to import inev_sdk
sdk_dir = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_dir))
