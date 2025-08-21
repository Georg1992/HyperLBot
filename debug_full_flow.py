#!/usr/bin/env python3
"""
Debug script to test the full prediction and entry analysis flow
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot
import json
import asyncio

def test_full_flow():
    """Test the complete trading flow to see where predictions get filtered out"""
    try:
        # Create paper trading bot
        print("🚀 Initializing Paper Trading Bot...")
        bot = YahooHyperliquidPaperTradingBot()
        
        print("✅ Bot initialized successfully")
        print()
        
        # Create mock market data
        mock_binance_analysis = {
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
        
        print("🔍 Testing full market analysis flow...")
        print(f"Current Price: ${current_price:,.2f}")
        print()
        
        # Call the bot's should_trade method directly
        analysis_result = bot.should_trade(current_price, mock_binance_analysis)
        
        print("📊 Analysis Result:")
        print(f"Should Trade: {analysis_result.get('should_trade', False)}")
        print(f"Reason: {analysis_result.get('reason', 'No reason provided')}")
        
        if 'signal_data' in analysis_result:
            signal_data = analysis_result['signal_data']
            print("📈 Signal Data:")
            print(f"   Side: {signal_data.get('side', 'UNKNOWN')}")
            print(f"   Entry Price: ${signal_data.get('entry_price', 0):,.2f}")
            print(f"   Target Price: ${signal_data.get('target_price', 0):,.2f}")
            print(f"   Stop Loss: ${signal_data.get('stop_loss', 0):,.2f}")
            print(f"   Prediction Type: {signal_data.get('prediction_type', 'UNKNOWN')}")
            print(f"   Confidence: {signal_data.get('prediction_confidence', 0)*100:.1f}%")
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ Error testing full flow: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_full_flow()
    if result:
        print("\n✅ Full flow test completed")
        if result.get('should_trade', False):
            print("🎯 Trade signal would be generated!")
        else:
            print("❌ No trade signal generated")
            print(f"Reason: {result.get('reason', 'Unknown reason')}")
    else:
        print("\n❌ Full flow test failed")
