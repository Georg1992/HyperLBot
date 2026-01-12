#!/usr/bin/env python3
"""
SR Weight Info - Helper to get weights file information for dashboard
Simple utility to check if trained weights exist and get metadata
"""

import os
import json
import time
from typing import Dict, Any, Optional
from loguru import logger


def get_weights_info(weights_dir: str = "data/sr_weights", method: str = "elasticnet") -> Dict[str, Any]:
    """
    Get information about trained weights file (for dashboard display)
    
    Args:
        weights_dir: Directory containing weights files
        method: Method name (default: "elasticnet")
        
    Returns:
        Dictionary with weights information:
        - exists: bool - whether weights file exists
        - file_path: str - path to weights file
        - age_days: float - age of weights in days
        - timestamp: float - file modification timestamp
        - method: str - training method
        - weights: dict - actual weights (if file exists and valid)
        - training_needed: str - training recommendation ("needed", "recommended", "up_to_date")
    """
    filename = f"{method}_weights.json"
    filepath = os.path.join(weights_dir, filename)
    
    info = {
        "exists": False,
        "file_path": filepath,
        "age_days": None,
        "timestamp": None,
        "method": method,
        "weights": None,
        "training_needed": "needed"  # Default: training needed if no weights
    }
    
    if not os.path.exists(filepath):
        return info
    
    try:
        file_time = os.path.getmtime(filepath)
        age_days = (time.time() - file_time) / 86400.0
        
        info["exists"] = True
        info["timestamp"] = file_time
        info["age_days"] = age_days
        
        # Determine training recommendation based on age
        if age_days < 30:
            info["training_needed"] = "up_to_date"
        elif age_days < 90:
            info["training_needed"] = "recommended"
        else:
            info["training_needed"] = "needed"
        
        # Try to load weights for display
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                info["weights"] = data.get("weights")
        except Exception as e:
            logger.debug(f"Could not load weights from file for info: {e}")
        
        return info
        
    except Exception as e:
        logger.debug(f"Could not get weights file info: {e}")
        return info
