#!/usr/bin/env python3
"""
Level data utilities - Single source of truth for level data retrieval
"""

from typing import Dict, Any, Optional


def get_level_power(level_data: Dict[str, Any], default: float = 50.0) -> float:
    """
    Get level power from level_data with consistent fallback logic
    
    Args:
        level_data: Level data dictionary
        default: Default value if power not found (default: 50.0)
        
    Returns:
        Level power (0-100)
    """
    if not level_data:
        return default
    
    # Try power first (new field), then strength_score (old field), then default
    power = level_data["power"] if "power" in level_data else None
    if power is not None:
        return float(power)
    
    strength_score = level_data.get("strength_score")
    if strength_score is not None:
        return float(strength_score)
    
    return default
