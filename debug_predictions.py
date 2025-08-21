#!/usr/bin/env python3
"""
Debug script to test prediction engine functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.prediction_engine import PredictionEngine
from core.config import TradingConfig
import json

def test_prediction_engine():
    """Test the prediction engine with sample data"""
    try:
        # Load config
        config = TradingConfig()
        
        # Create prediction engine
        prediction_engine = PredictionEngine(config.STRATEGY_CONFIGS['standard'])
        
        # Sample data - minimal required structure
        sample_binance_analysis = {
            "candles_5m": [
                {"timestamp": 1640000000, "open": 113000, "high": 113500, "low": 112500, "close": 113200, "volume": 100},
                {"timestamp": 1640000300, "open": 113200, "high": 113800, "low": 113000, "close": 113600, "volume": 120},
                {"timestamp": 1640000600, "open": 113600, "high": 114000, "low": 113400, "close": 113800, "volume": 110},
                {"timestamp": 1640000900, "open": 113800, "high": 114200, "low": 113600, "close": 114000, "volume": 130},
                {"timestamp": 1640001200, "open": 114000, "high": 114300, "low": 113900, "close": 114100, "volume": 115},
                {"timestamp": 1640001500, "open": 114100, "high": 114500, "low": 114000, "close": 114300, "volume": 125},
                {"timestamp": 1640001800, "open": 114300, "high": 114600, "low": 114200, "close": 114500, "volume": 135},
                {"timestamp": 1640002100, "open": 114500, "high": 114800, "low": 114400, "close": 114700, "volume": 140},
                {"timestamp": 1640002400, "open": 114700, "high": 115000, "low": 114600, "close": 114900, "volume": 150},
                {"timestamp": 1640002700, "open": 114900, "high": 115200, "low": 114800, "close": 115000, "volume": 145}
            ],
            "candles_1h": [
                {"timestamp": 1640000000, "open": 113000, "high": 115200, "low": 112500, "close": 115000, "volume": 1200},
                {"timestamp": 1640003600, "open": 115000, "high": 115500, "low": 114500, "close": 114800, "volume": 1100},
                {"timestamp": 1640007200, "open": 114800, "high": 115300, "low": 114200, "close": 114900, "volume": 1300},
                {"timestamp": 1640010800, "open": 114900, "high": 115400, "low": 114600, "close": 115100, "volume": 1250},
                {"timestamp": 1640014400, "open": 115100, "high": 115600, "low": 114900, "close": 115300, "volume": 1180},
                {"timestamp": 1640018000, "open": 115300, "high": 115800, "low": 115000, "close": 115500, "volume": 1220},
                {"timestamp": 1640021600, "open": 115500, "high": 116000, "low": 115200, "close": 115700, "volume": 1350},
                {"timestamp": 1640025200, "open": 115700, "high": 116200, "low": 115400, "close": 115900, "volume": 1400},
                {"timestamp": 1640028800, "open": 115900, "high": 116500, "low": 115600, "close": 116200, "volume": 1500},
                {"timestamp": 1640032400, "open": 116200, "high": 116800, "low": 115900, "close": 116500, "volume": 1450}
            ],
            "trend_5m": {
                "trend": "UP",
                "strength": 0.7,
                "direction": "bullish"
            },
            "trend_1h": {
                "trend": "UP", 
                "strength": 0.6,
                "direction": "bullish"
            },
            "support_resistance_5m": {
                "support": 114500,
                "resistance": 116000,
                "range": 1500
            }
        }
        
        current_price = 115000
        strategy_name = "standard"
        
        print("🔍 Testing Prediction Engine...")
        print(f"Current Price: ${current_price:,.2f}")
        print(f"Strategy: {strategy_name}")
        print()
        
        # Test prediction generation
        print("🔧 Debug info:")
        print(f"   Support: ${sample_binance_analysis['support_resistance_5m']['support']:,.2f}")
        print(f"   Resistance: ${sample_binance_analysis['support_resistance_5m']['resistance']:,.2f}")
        print(f"   Range: ${sample_binance_analysis['support_resistance_5m']['range']:,.2f}")
        print(f"   5m Trend: {sample_binance_analysis['trend_5m']}")
        print(f"   1h Trend: {sample_binance_analysis['trend_1h']}")
        print()
        
        # Test confidence calculation directly
        test_confidence = prediction_engine._calculate_momentum_confidence(
            sample_binance_analysis['trend_1h'], 
            sample_binance_analysis['trend_5m'], 
            0.003
        )
        print(f"   Direct confidence calc: {test_confidence:.3f}")
        print()
        
        result = prediction_engine.build_price_prediction(
            sample_binance_analysis, 
            current_price, 
            strategy_name
        )
        
        print("📊 Prediction Result:")
        print(f"Has Prediction: {result.get('has_prediction', False)}")
        print(f"Reason: {result.get('reason', 'No reason provided')}")
        print(f"Mode: {result.get('prediction_mode', 'UNKNOWN')}")
        print()
        
        if result.get('has_prediction', False):
            best_prediction = result.get('best_prediction', {})
            all_predictions = result.get('all_predictions', [])
            
            print(f"🎯 Best Prediction:")
            print(f"   Type: {best_prediction.get('type', 'UNKNOWN')}")
            print(f"   Entry Price: ${best_prediction.get('entry_price', 0):,.2f}")
            print(f"   Side: {best_prediction.get('side', 'UNKNOWN')}")
            print(f"   Confidence: {best_prediction.get('confidence', 0):.1f}%")
            print(f"   Timeframe: {best_prediction.get('timeframe', 0)} minutes")
            print(f"   Reason: {best_prediction.get('reason', 'No reason')}")
            print()
            
            print(f"📈 All Predictions ({len(all_predictions)}):")
            for i, pred in enumerate(all_predictions):
                print(f"   {i+1}. {pred.get('type', 'UNKNOWN')} - {pred.get('side', 'UNKNOWN')} @ ${pred.get('entry_price', 0):,.2f} (Confidence: {pred.get('confidence', 0):.1f}%)")
        else:
            print("❌ No predictions generated")
            
        return result
        
    except Exception as e:
        print(f"❌ Error testing prediction engine: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_prediction_engine()
    if result:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed")
