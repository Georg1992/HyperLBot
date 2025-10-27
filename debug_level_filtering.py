#!/usr/bin/env python3
"""
Debug why closer resistance levels are being filtered out
"""

import sys
sys.path.append('.')

from core.calculations.support_resistance_calculator import SupportResistanceCalculator
from core.services.centralized_cache import CentralizedCache
from core.services.historical_data_service import HistoricalDataService

def debug_level_filtering():
    """Debug why closer resistance levels are being filtered out"""
    
    # Create instances
    cache = CentralizedCache()
    historical_service = HistoricalDataService()
    sr_calc = SupportResistanceCalculator('BTC', cache=cache)
    
    current_price = 114842.5
    print(f"Current price: ${current_price:,.2f}")
    print()
    
    # Get the raw result before filtering
    result = sr_calc.calculate_multi_timeframe_levels(current_price)
    
    print("Raw S/R Result:")
    print("Status:", result.get('status'))
    print("Levels count:", len(result.get('levels', [])))
    print()
    
    # Show ALL levels (before confidence filtering)
    levels = result.get('levels', [])
    print("ALL levels detected (before confidence filtering):")
    for i, level in enumerate(levels):
        price = level.get('price_level', 0)
        score = level.get('strength_score', 0)
        level_type = level.get('type', 'unknown')
        touches = level.get('touches', 0)
        distance = abs(price - current_price)
        print(f"  {i+1}. ${price:,.0f} - Score: {score:.1f} - {level_type} - {touches}x touches - {distance:,.0f} away")
    
    print()
    
    # Show resistance levels specifically
    resistance_levels = [l for l in levels if l.get('type') == 'resistance' and l.get('price_level', 0) > current_price]
    print(f"Resistance levels above current price ({len(resistance_levels)}):")
    for i, level in enumerate(resistance_levels):
        price = level.get('price_level', 0)
        score = level.get('strength_score', 0)
        touches = level.get('touches', 0)
        distance = price - current_price
        print(f"  {i+1}. ${price:,.0f} - Score: {score:.1f} - {touches}x touches - {distance:,.0f} above")
    
    print()
    
    # Show which ones pass the 30.0 threshold
    passing_resistance = [l for l in resistance_levels if l.get('strength_score', 0) >= 30.0]
    print(f"Resistance levels passing 30.0 threshold ({len(passing_resistance)}):")
    for i, level in enumerate(passing_resistance):
        price = level.get('price_level', 0)
        score = level.get('strength_score', 0)
        touches = level.get('touches', 0)
        distance = price - current_price
        print(f"  {i+1}. ${price:,.0f} - Score: {score:.1f} - {touches}x touches - {distance:,.0f} above")
    
    print()
    
    # Show which ones are filtered out
    filtered_resistance = [l for l in resistance_levels if l.get('strength_score', 0) < 30.0]
    print(f"Resistance levels filtered out (< 30.0 threshold) ({len(filtered_resistance)}):")
    for i, level in enumerate(filtered_resistance):
        price = level.get('price_level', 0)
        score = level.get('strength_score', 0)
        touches = level.get('touches', 0)
        distance = price - current_price
        print(f"  {i+1}. ${price:,.0f} - Score: {score:.1f} - {touches}x touches - {distance:,.0f} above")

if __name__ == "__main__":
    debug_level_filtering()
