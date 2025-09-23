"""
Core module - HyperLBot
Contains core functionality including configuration, API clients, and logging
"""

import os
import sys

# Add project root to Python path for easy importing
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root if not already present
if project_root not in sys.path:
    sys.path.insert(0, project_root)
