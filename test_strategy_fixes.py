#!/usr/bin/env python3
"""
Test script to verify strategy selection fixes
"""

import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config.config import TradingConfig
from core.services.strategy_manager import StrategyManager

def test_strategy_selection():
    """Test the fixed strategy selection logic"""
    print("[TEST] Testing Strategy Selection Fixes...")
    
    # Initialize strategy manager
    config = TradingConfig()
    strategy_manager = StrategyManager(config)
    
    # Test cases with different market conditions
    test_cases = [
        {
            "name": "Extreme Volatility + High Volume",
            "market_data": {
                "volatility_category": "EXTREME",
                "trend_direction": "SIDEWAYS",
                "volume_category": "HIGH",
                "volatility_5m": 0.06,  # 6%
                "rsi_value": 50.0
            },
            "expected_strategy": "spike_hunting"
        },
        {
            "name": "Moderate Volatility + Good RSI + Decent Volume",
            "market_data": {
                "volatility_category": "MODERATE",
                "trend_direction": "SIDEWAYS",
                "volume_category": "NORMAL",
                "volatility_5m": 0.02,  # 2%
                "rsi_value": 45.0
            },
            "expected_strategy": "scalping"
        },
        {
            "name": "High Volatility + Strong Trend",
            "market_data": {
                "volatility_category": "HIGH",
                "trend_direction": "BULLISH",
                "volume_category": "HIGH",
                "volatility_5m": 0.04,  # 4%
                "rsi_value": 60.0
            },
            "expected_strategy": "trend_following"
        },
        {
            "name": "Low Volatility + Sideways Trend",
            "market_data": {
                "volatility_category": "LOW",
                "trend_direction": "SIDEWAYS",
                "volume_category": "NORMAL",
                "volatility_5m": 0.005,  # 0.5%
                "rsi_value": 50.0
            },
            "expected_strategy": "low_volatility_range"
        },
        {
            "name": "Moderate Volatility + Sideways Trend",
            "market_data": {
                "volatility_category": "MODERATE",
                "trend_direction": "SIDEWAYS",
                "volume_category": "NORMAL",
                "volatility_5m": 0.015,  # 1.5%
                "rsi_value": 50.0
            },
            "expected_strategy": "range_trading"
        }
    ]
    
    # Run tests
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\n[TEST] {test_case['name']}")
        
        try:
            # Reset manager state to avoid cooldown and previous strategy influence
            strategy_manager.current_strategy = 'standard'
            strategy_manager.last_strategy_switch = 0
            if hasattr(strategy_manager, '_last_market_data'):
                delattr(strategy_manager, '_last_market_data')
            
            # Test strategy selection
            selected_strategy = strategy_manager.detect_optimal_strategy(test_case['market_data'])
            
            if selected_strategy == test_case['expected_strategy']:
                print(f"PASS: Selected {selected_strategy} (expected {test_case['expected_strategy']})")
                passed += 1
            else:
                print(f"FAIL: Selected {selected_strategy} (expected {test_case['expected_strategy']})")
                failed += 1
                
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
    
    # Test fallback logic removal
    print(f"\n[TEST] Fallback Logic Removal...")
    try:
        # Reset state
        strategy_manager.current_strategy = 'standard'
        strategy_manager.last_strategy_switch = 0
        if hasattr(strategy_manager, '_last_market_data'):
            delattr(strategy_manager, '_last_market_data')
        
        # Test with incompatible strategy (should find alternative, not fallback to standard)
        incompatible_data = {
            "volatility_category": "LOW",
            "trend_direction": "BULLISH",  # Incompatible with low_volatility_range
            "volume_category": "LOW",
            "volatility_5m": 0.001,
            "rsi_value": 30.0
        }
        
        selected_strategy = strategy_manager.detect_optimal_strategy(incompatible_data)
        print(f"Selected {selected_strategy} (should not be 'standard' fallback)")
        
        if selected_strategy != "standard":
            print("PASS: No fallback to standard strategy")
            passed += 1
        else:
            print("FAIL: Still using standard fallback")
            failed += 1
            
    except Exception as e:
        print(f"ERROR in fallback test: {e}")
        failed += 1
    
    # Summary
    print(f"\n[SUMMARY]")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    total = passed + failed
    success_rate = (passed/total*100) if total else 0
    print(f"   Success Rate: {success_rate:.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    success = test_strategy_selection()
    if success:
        print("\nAll tests passed! Strategy selection fixes are working correctly.")
    else:
        print("\nSome tests failed. Please review the fixes.")
    
    sys.exit(0 if success else 1)
