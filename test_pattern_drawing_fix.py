import sys
sys.path.append('.')

from core.services.dashboard_service import DashboardService
import json

def test_pattern_drawing_fix():
    print("Testing pattern drawing fix with real backend data structure...")
    
    try:
        # Create dashboard service
        dashboard_service = DashboardService()
        
        # Create mock market data with the EXACT structure from the backend
        mock_market_data = {
            "timestamp": 1761574800,
            "current_price": 114550.0,
            "strategy": "standard",
            "patterns": {
                "patterns": {
                    "candlestick_patterns": [
                        {
                            "pattern": "BULLISH_ENGULFING",
                            "type": "REVERSAL",
                            "direction": "BULLISH",
                            "confidence": 0.53,
                            "indices": [18, 19],
                            "start_candle_index": 18,
                            "end_candle_index": 19,
                            "pattern_high": 114600.0,
                            "pattern_low": 114500.0,
                        }
                    ],
                    "reversal_patterns": [],
                    "continuation_patterns": [],
                    "triangle_patterns": [],
                    "channel_patterns": [],
                    "wedge_patterns": [],
                    "trend_patterns": []
                },
                "overall_confidence": 0.53,
                "market_setup": "BULLISH",
                "pattern_count": 1,
                "timestamp": 1761574800,
                "data_source": "pattern_recognition_engine"
            }
        }
        
        # Update dashboard with mock data
        dashboard_service.update_market_data(mock_market_data)
        
        # Get the updated data
        dashboard_data = dashboard_service.get_data()
        market_data = dashboard_data.get("market", {})
        
        print(f"Dashboard data keys: {list(dashboard_data.keys())}")
        print(f"Market data keys: {list(market_data.keys())}")
        
        # Check if candleData was created
        if "candleData" in market_data:
            candle_data = market_data["candleData"]
            print(f"CandleData keys: {list(candle_data.keys())}")
            
            if "pattern_analysis" in candle_data:
                pattern_analysis = candle_data["pattern_analysis"]
                print(f"Pattern analysis keys: {list(pattern_analysis.keys())}")
                
                if "patterns" in pattern_analysis:
                    patterns = pattern_analysis["patterns"]
                    print(f"Patterns structure: {type(patterns)}")
                    
                    if isinstance(patterns, dict):
                        print(f"Pattern categories: {list(patterns.keys())}")
                        
                        if "candlestick_patterns" in patterns:
                            candlestick_patterns = patterns["candlestick_patterns"]
                            print(f"Number of candlestick patterns: {len(candlestick_patterns)}")
                            
                            for i, pattern in enumerate(candlestick_patterns):
                                print(f"Pattern {i+1}: {pattern['pattern']} (confidence: {pattern['confidence']})")
                                print(f"  - Direction: {pattern['direction']}")
                                print(f"  - Indices: {pattern['indices']}")
                                print(f"  - High: {pattern['pattern_high']}, Low: {pattern['pattern_low']}")
                        
                    print("SUCCESS: Pattern data structure matches backend format!")
                else:
                    print("ERROR: No patterns found in pattern_analysis")
            else:
                print("ERROR: No pattern_analysis found in candleData")
        else:
            print("ERROR: No candleData found in market data")
            
        # Save the data to see the structure
        with open("test_pattern_drawing_data.json", "w") as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        print("INFO: Dashboard data saved to test_pattern_drawing_data.json")
        
    except Exception as e:
        print(f"ERROR: Error testing pattern drawing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pattern_drawing_fix()
