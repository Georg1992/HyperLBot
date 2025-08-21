"""
Core module - HyperLBot
Contains core functionality including configuration, API clients, and logging
"""

import os
import sys

# Add project paths to Python path for easy importing
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
core_path = os.path.join(project_root, 'core')
data_path = os.path.join(project_root, 'data')
strategies_path = os.path.join(project_root, 'strategies')

# Add all paths if not already present
for path in [core_path, data_path, strategies_path]:
    if path not in sys.path:
        sys.path.insert(0, path)