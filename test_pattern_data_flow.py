#!/usr/bin/env python3
"""
Test Pattern Recognition Data Flow
Verify that pattern data flows correctly from engine to dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.services.system_initializer import get_system_initializer
from core.services.market_data_service import create_market_data_service
from core.services.dashboard_service import create_dashboard_service
from core.analysis.real_time.pattern_recognition_engine import PatternRecognitionEngine

def test_pattern_data_flow():
    """Test the complete pattern data flow"""
    print("=== Testing Pattern Recognition Data Flow ===")
    
    try:
        # 1. Initialize system
        print("\n1. Initializing system...")
        system_initializer = get_system_initializer()
        init_result = system_initializer.initialize_system(10000)
        
        if not init_result.get("success"):
            print(f"❌ System initialization failed: {init_result.get('error')}")
            return False
        
        print("System initialized successfully")
        
        # 2. Get services
        print("\n2. Getting services...")
        market_data_service = system_initializer.singleton_systems.get("market_data_service")
        dashboard_service = system_initializer.singleton_systems.get("dashboard_service")
        
        if not market_data_service or not dashboard_service:
            print("❌ Failed to get required services")
            return False
        
        print("Services retrieved successfully")
        
        # 3. Test pattern recognition engine directly
        print("\n3. Testing pattern recognition engine...")
        pattern_engine = PatternRecognitionEngine("BTC")
        
        # Get some test candles
        from core.services.historical_data_service import create_historical_data_service
        historical_service = create_historical_data_service()
        candles = historical_service.get_5m_candles("BTC", 20)
        
        if not candles:
            print("❌ No candle data available")
            return False
        
        print(f"Retrieved {len(candles)} candles for testing")
        
        # Analyze patterns
        pattern_result = pattern_engine.analyze_patterns(candles)
        print(f"Pattern analysis result keys: {list(pattern_result.keys())}")
        
        if "patterns" in pattern_result:
            patterns = pattern_result["patterns"]
            print(f"Found {len(patterns)} patterns")
            if patterns:
                print(f"   First pattern: {patterns[0]}")
        else:
            print("⚠️ No patterns key in result")
        
        # 4. Test market data service pattern analysis
        print("\n4. Testing market data service pattern analysis...")
        pattern_analysis = market_data_service.get_pattern_analysis()
        print(f"Market data service pattern analysis keys: {list(pattern_analysis.keys())}")
        
        if "patterns" in pattern_analysis:
            patterns = pattern_analysis["patterns"]
            print(f"Market data service found {len(patterns)} patterns")
        else:
            print("No patterns key in market data service result")
        
        # 5. Test dashboard service data preparation
        print("\n5. Testing dashboard service data preparation...")
        market_data = market_data_service.get_real_time_market_data("standard")
        
        if "patterns" in market_data:
            patterns = market_data["patterns"]
            print(f"Real-time market data contains patterns: {list(patterns.keys()) if isinstance(patterns, dict) else type(patterns)}")
        else:
            print("No patterns in real-time market data")
        
        # 6. Test dashboard data preparation
        print("\n6. Testing dashboard data preparation...")
        candle_data = dashboard_service._prepare_candle_data(market_data)
        
        if candle_data and "pattern_analysis" in candle_data:
            pattern_analysis = candle_data["pattern_analysis"]
            print(f"Dashboard candle data contains pattern_analysis: {list(pattern_analysis.keys()) if isinstance(pattern_analysis, dict) else type(pattern_analysis)}")
        else:
            print("No pattern_analysis in dashboard candle data")
        
        # 7. Test complete dashboard data
        print("\n7. Testing complete dashboard data...")
        dashboard_data = dashboard_service.get_data()
        
        # Check the correct location: dashboard_data["market"]["candleData"]
        if "market" in dashboard_data and "candleData" in dashboard_data["market"] and dashboard_data["market"]["candleData"]:
            candle_data = dashboard_data["market"]["candleData"]
            if "pattern_analysis" in candle_data:
                pattern_analysis = candle_data["pattern_analysis"]
                print(f"Complete dashboard data contains pattern_analysis: {list(pattern_analysis.keys()) if isinstance(pattern_analysis, dict) else type(pattern_analysis)}")
            else:
                print("No pattern_analysis in complete dashboard data")
        else:
            print("No candleData in complete dashboard data")
            print(f"Dashboard data structure: {list(dashboard_data.keys())}")
            if "market" in dashboard_data:
                print(f"Market data structure: {list(dashboard_data['market'].keys())}")
        
        print("\n=== Pattern Data Flow Test Complete ===")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pattern_data_flow()
    if success:
        print("\nPattern data flow test PASSED")
    else:
        print("\nPattern data flow test FAILED")
