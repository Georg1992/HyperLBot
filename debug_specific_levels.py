#!/usr/bin/env python3
"""
Debug why levels like $115,784 and $113,888 are not showing as resistance
"""

import sys
sys.path.append('.')

from core.calculations.support_resistance_calculator import SupportResistanceCalculator
from core.services.centralized_cache import CentralizedCache
from core.services.historical_data_service import HistoricalDataService

def debug_specific_levels():
    """Debug why specific levels are not showing as resistance"""
    
    # Create instances
    cache = CentralizedCache()
    historical_service = HistoricalDataService()
    sr_calc = SupportResistanceCalculator('BTC', cache=cache)
    
    current_price = 114842.5
    print(f"Current price: ${current_price:,.2f}")
    print()
    
    # Get the raw result
    result = sr_calc.calculate_multi_timeframe_levels(current_price)
    
    # Show ALL levels with detailed info
    levels = result.get('levels', [])
    print("ALL levels with detailed classification:")
    for i, level in enumerate(levels):
        price = level.get('price_level', 0)
        score = level.get('strength_score', 0)
        level_type = level.get('type', 'unknown')
        touches = level.get('touches', 0)
        distance = abs(price - current_price)
        mtf_count = level.get('mtf_count', 0)
        status = level.get('status', 'unknown')
        
        print(f"  {i+1}. ${price:,.0f} - Score: {score:.1f} - {level_type} - {touches}x touches - {distance:,.0f} away - MTF: {mtf_count} - Status: {status}")
        
        # Check if this should be resistance but is classified as support
        if price > current_price and level_type == 'support':
            print(f"      *** ERROR: ${price:,.0f} is above current price but classified as SUPPORT! ***")
        elif price < current_price and level_type == 'resistance':
            print(f"      *** ERROR: ${price:,.0f} is below current price but classified as RESISTANCE! ***")
    
    print()
    
    # Check for levels that should be resistance
    print("Levels that should be resistance (above current price):")
    for level in levels:
        price = level.get('price_level', 0)
        if price > current_price:
            level_type = level.get('type', 'unknown')
            score = level.get('strength_score', 0)
            touches = level.get('touches', 0)
            distance = price - current_price
            print(f"  ${price:,.0f} - {level_type} - Score: {score:.1f} - {touches}x touches - {distance:,.0f} above")

if __name__ == "__main__":
    debug_specific_levels()
