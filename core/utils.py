#!/usr/bin/env python3
"""
Simple utility functions to reduce code duplication
No overcomplication - just practical helper functions
"""

from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

def validate_candles(candles: List[Dict], min_count: int = 1, check_fields: List[str] = None) -> Tuple[bool, str]:
    """
    Simple candle validation to eliminate duplicate validation patterns
    
    Args:
        candles: List of candle dictionaries
        min_count: Minimum required number of candles
        check_fields: Fields to check (default: ['close'])
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    check_fields = check_fields or ['close']
    
    # Basic checks
    if not candles or not isinstance(candles, list):
        return False, "no_candles"
    
    if len(candles) < min_count:
        return False, f"insufficient_candles_{len(candles)}_need_{min_count}"
    
    # Check first few candles for required fields
    for i, candle in enumerate(candles[:3]):
        if not isinstance(candle, dict):
            return False, f"candle_{i}_not_dict"
        
        for field in check_fields:
            if field not in candle or candle[field] is None:
                return False, f"missing_{field}_in_candle_{i}"
            
            # Check numeric fields
            if field in ['open', 'high', 'low', 'close', 'volume']:
                try:
                    value = float(candle[field])
                    if value < 0:
                        return False, f"negative_{field}_in_candle_{i}"
                except (ValueError, TypeError):
                    return False, f"invalid_{field}_in_candle_{i}"
    
    return True, "valid"

def safe_float_convert(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with fallback"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_percentage_cap(value: Any, max_value: float = 1.0) -> float:
    """Cap percentage values to prevent unrealistic inflation"""
    try:
        float_value = safe_float_convert(value, 0.0)
        return max(0.0, min(float_value, max_value))
    except:
        return 0.0

def validate_price(price: Any, field_name: str = "price") -> Tuple[bool, str]:
    """Simple price validation"""
    if price is None:
        return False, f"{field_name}_is_none"
    
    try:
        price_float = float(price)
        if price_float <= 0:
            return False, f"{field_name}_not_positive"
        if price_float > 1_000_000:  # Sanity check
            return False, f"{field_name}_unrealistic"
        return True, "valid"
    except (ValueError, TypeError):
        return False, f"{field_name}_not_numeric"

def log_error_with_context(error: Exception, context: str, additional_info: Dict[str, Any] = None):
    """Simple error logging with context"""
    logger.error(f"❌ Error in {context}: {type(error).__name__}: {error}")
    if additional_info:
        for key, value in additional_info.items():
            logger.error(f"   {key}: {value}")