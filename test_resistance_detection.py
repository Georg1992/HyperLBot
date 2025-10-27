#!/usr/bin/env python3
"""
Test script to debug resistance level detection near current price
"""

import sys
sys.path.append('.')

from core.calculations.support_resistance_calculator import SupportResistanceCalculator
from core.services.centralized_cache import CentralizedCache
from core.services.historical_data_service import HistoricalDataService
from core.calculations.sr_data_provider import SRDataProvider
from core.calculations.sr_detector import SRDetector

def test_resistance_detection():
    """Test why resistance levels aren't detected near current price"""
    
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
    
    if not candles_5m:
        print("No 5m candles available!")
        return
    
    # Find recent candles above current price
    recent_candles = candles_5m[-100:]  # Last 100 candles
    above_price_candles = [c for c in recent_candles if c.get('high', 0) > current_price]
    
    print(f"Candles above current price in last 100: {len(above_price_candles)}")
    
    if above_price_candles:
        max_high = max(c.get('high', 0) for c in above_price_candles)
        min_high = min(c.get('high', 0) for c in above_price_candles)
        print(f"Price range above current: ${min_high:,.2f} - ${max_high:,.2f}")
        print()
        
        # Show some examples
        print("Sample candles above current price:")
        for i, candle in enumerate(above_price_candles[:5]):
            high = candle.get('high', 0)
            timestamp = candle.get('timestamp', 0)
            print(f"  ${high:,.2f} (timestamp: {timestamp})")
        print()
    
    # Test swing point detection on 5m candles
    print("Testing swing point detection on 5m candles...")
    swing_points = detector.detect_swing_points(candles_5m, current_price, n=1, timeframe="5m", atr=atr_5m)
    
    print(f"Total swing points detected: {len(swing_points)}")
    
    # Filter resistance levels (above current price)
    resistance_levels = [sp for sp in swing_points if sp.level > current_price]
    print(f"Resistance levels (above current price): {len(resistance_levels)}")
    
    if resistance_levels:
        print("\nResistance levels detected:")
        for level in resistance_levels[:10]:  # Show first 10
            distance = level.level - current_price
            print(f"  ${level.level:,.2f} - {distance:,.0f} above current price")
    else:
        print("No resistance levels detected!")
        
        # Debug: check if any candles have highs above current price
        all_highs_above = [c.get('high', 0) for c in candles_5m if c.get('high', 0) > current_price]
        print(f"Candles with highs above current price: {len(all_highs_above)}")
        
        if all_highs_above:
            print("Sample highs above current price:")
            for high in sorted(all_highs_above)[:10]:
                print(f"  ${high:,.2f}")

if __name__ == "__main__":
    test_resistance_detection()
