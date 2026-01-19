#!/usr/bin/env python3
"""
Distance calculation utilities - Single source of truth for distance calculations
"""

from typing import Optional


def calculate_distance_pct(price1: float, price2: float, reference_price: float) -> float:
    """
    Calculate distance between two prices as percentage of reference price
    
    Args:
        price1: First price
        price2: Second price
        reference_price: Reference price for percentage calculation (usually current_price)
        
    Returns:
        Distance as percentage (e.g., 0.01 = 1%)
    """
    if reference_price <= 0:
        return 0.0
    
    distance = abs(price1 - price2)
    distance_pct = distance / reference_price
    
    return distance_pct


def calculate_distance_atr(distance_pct: float, atr_pct: float) -> float:
    """
    Calculate distance in ATR units
    
    Args:
        distance_pct: Distance as percentage
        atr_pct: ATR as percentage
        
    Returns:
        Distance in ATR units (e.g., 2.5 = 2.5×ATR)
    """
    if atr_pct <= 0:
        return 10.0  # Default to large value if ATR unavailable
    
    distance_atr = distance_pct / atr_pct
    return distance_atr


def calculate_entry_to_level_distance(entry_price: float, level_price: float, current_price: float) -> tuple[float, float]:
    """
    Calculate distance from entry price to level price
    
    Args:
        entry_price: Entry price
        level_price: S/R level price
        current_price: Current market price (for percentage calculation)
        
    Returns:
        (distance_pct, distance_atr) tuple
    """
    distance_pct = calculate_distance_pct(entry_price, level_price, current_price)
    
    # Calculate ATR percentage (simplified - caller should provide atr_pct if available)
    # This is a fallback - ideally caller should use calculate_distance_atr with actual atr_pct
    atr_pct = 0.004  # Default 0.4% ATR estimate
    distance_atr = calculate_distance_atr(distance_pct, atr_pct)
    
    return distance_pct, distance_atr
