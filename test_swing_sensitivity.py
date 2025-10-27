#!/usr/bin/env python3
"""
Test different swing detection sensitivity to find resistance levels closer to current price
"""

import sys
sys.path.append('.')

from core.calculations.support_resistance_calculator import SupportResistanceCalculator
from core.services.centralized_cache import CentralizedCache
from core.services.historical_data_service import HistoricalDataService
from core.calculations.sr_data_provider import SRDataProvider
from core.calculations.sr_detector import SRDetector

def test_swing_sensitivity():
    """Test different swing detection sensitivity values"""
    
    # Create instances
    cache = CentralizedCache()
    historical_service = HistoricalDataService()
    data_provider = SRDataProvider('BTC', historical_service, cache)
    detector = SRDetector()
    
    current_price = 114842.5
    print(f"Current price: ${current_price:,.2f}")
    print()
    
    # Get recent candles for 5m timeframe
    candles_data, atr_per_tf = data_provider.fetch_multi_timeframe_data(current_price)
    candles_5m = candles_data.get('5m', [])
    atr_5m = atr_per_tf.get('5m', 0)
    
    print(f"5m candles count: {len(candles_5m)}")
    print(f"ATR 5m: ${atr_5m:.2f}")
    print()
    
    # Test different n values
    for n in [1, 2, 3, 4, 5]:
        print(f"Testing n={n} (swing detection sensitivity):")
        
        swing_points = detector.detect_swing_points(candles_5m, current_price, n=n, timeframe="5m", atr=atr_5m)
        resistance_levels = [sp for sp in swing_points if sp.level > current_price]
        
        print(f"  Total swing points: {len(swing_points)}")
        print(f"  Resistance levels: {len(resistance_levels)}")
        
        if resistance_levels:
            # Show closest resistance levels
            closest_resistance = min(resistance_levels, key=lambda x: x.level - current_price)
            distance = closest_resistance.level - current_price
            print(f"  Closest resistance: ${closest_resistance.level:,.2f} ({distance:,.0f} above)")
            
            # Show all resistance levels within $2000 of current price
            nearby_resistance = [r for r in resistance_levels if (r.level - current_price) <= 2000]
            print(f"  Resistance within $2000: {len(nearby_resistance)}")
            
            if nearby_resistance:
                print("  Nearby resistance levels:")
                for level in sorted(nearby_resistance, key=lambda x: x.level)[:5]:
                    distance = level.level - current_price
                    print(f"    ${level.level:,.2f} ({distance:,.0f} above)")
        print()

if __name__ == "__main__":
    test_swing_sensitivity()
