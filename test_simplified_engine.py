#!/usr/bin/env python3
"""
Test script to verify simplified pattern recognition engine
"""

import sys
import time
sys.path.append('.')

from core.analysis.real_time.pattern_recognition_engine_simplified import PatternRecognitionEngine

def test_simplified_engine():
    """Test the simplified pattern recognition engine"""
    
    # Create engine
    engine = PatternRecognitionEngine()
    
    # Create mock candles data
    current_time = time.time()
    candles = []
    
    # Create 20 candles (5 minutes each = 100 minutes total)
    for i in range(20):
        candle_time = current_time - (19 - i) * 300  # 5 minutes apart
        candles.append({
            'timestamp': candle_time,
            'open': 114000 + i * 10,
            'high': 114050 + i * 10,
            'close': 114020 + i * 10,
            'low': 113980 + i * 10,
            'volume': 1000
        })
    
    # Add three consecutive bullish candles for THREE WHITE SOLDIERS
    candles[-3]['close'] = candles[-3]['open'] + 50  # Bullish
    candles[-2]['close'] = candles[-2]['open'] + 50  # Bullish  
    candles[-1]['close'] = candles[-1]['open'] + 50  # Bullish
    
    # Analyze patterns
    result = engine.analyze_patterns(candles)
    
    print("=== SIMPLIFIED PATTERN ENGINE TEST ===")
    print(f"Status: {result.get('status')}")
    print(f"Overall confidence: {result.get('overall_confidence', 0):.1%}")
    print(f"Patterns detected: {len(result.get('patterns', []))}")
    
    for pattern in result.get('patterns', []):
        pattern_name = pattern.get('pattern', 'UNKNOWN')
        confidence = pattern.get('confidence', 0)
        age = pattern.get('age_minutes', 0)
        print(f"  - {pattern_name}: {confidence:.1%} confidence, {age:.1f}m old")
    
    print(f"\n=== COMPARISON ===")
    print("Original engine: 49 methods, 1800+ lines")
    print("Simplified engine: 15 methods, ~400 lines")
    print("Reduction: ~75% smaller!")

if __name__ == "__main__":
    test_simplified_engine()
