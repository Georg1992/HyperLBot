#!/usr/bin/env python3
"""
Test the enhanced prediction engine with RSI and volume integration
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot

def test_enhanced_predictions():
    """Test the enhanced predictions with RSI and volume data"""
    try:
        print("🚀 Testing Enhanced RSI & Volume Integration...")
        bot = YahooHyperliquidPaperTradingBot()
        
        if not bot.connect():
            print("❌ Failed to connect to APIs")
            return None
            
        print("✅ Connected to APIs successfully")
        
        # Get real market data
        yahoo_analysis = bot.get_yahoo_analysis()
        if not yahoo_analysis:
            print("❌ Failed to get Yahoo analysis")
            return None
            
        hyperliquid_price = bot.get_hyperliquid_price()
        if not hyperliquid_price:
            print("❌ Failed to get Hyperliquid price")
            return None
        
        print(f"📊 Current Market Snapshot:")
        print(f"   Yahoo Analysis Price: ${yahoo_analysis.get('current_price', 0):,.2f}")
        print(f"   Hyperliquid Real Price: ${hyperliquid_price:,.2f}")
        print(f"   Market Condition: {yahoo_analysis.get('market_condition', 'UNKNOWN')}")
        
        # Test the enhanced prediction
        print(f"\n🔍 Testing Enhanced Prediction Generation...")
        signal = bot.should_trade(hyperliquid_price, yahoo_analysis)
        
        print(f"\n📊 Enhanced Prediction Result:")
        print(f"Should Trade: {signal.get('should_trade', False)}")
        print(f"Reason: {signal.get('reason', 'No reason provided')}")
        
        # Check if signal data includes enhanced information
        if 'signal_data' in signal:
            signal_data = signal['signal_data']
            prediction_analysis = signal_data.get('prediction_analysis', {})
            
            print(f"\n🎯 Enhanced Prediction Details:")
            if prediction_analysis.get('has_prediction', False):
                best_pred = prediction_analysis.get('best_prediction', {})
                print(f"   Type: {best_pred.get('type', 'UNKNOWN')}")
                print(f"   Side: {best_pred.get('side', 'UNKNOWN')}")
                print(f"   Entry Price: ${best_pred.get('entry_price', 0):,.2f}")
                print(f"   Current Price: ${best_pred.get('current_price', 'N/A'):,.2f}" if isinstance(best_pred.get('current_price'), (int, float)) else f"   Current Price: {best_pred.get('current_price', 'N/A')}")
                print(f"   Confidence: {best_pred.get('confidence', 0)*100:.1f}%")
                print(f"   RSI Context: {best_pred.get('rsi_context', 'N/A'):.1f}" if isinstance(best_pred.get('rsi_context'), (int, float)) else f"   RSI Context: {best_pred.get('rsi_context', 'N/A')}")
                print(f"   Orderbook Depth: {best_pred.get('orderbook_depth', 'N/A'):.1f} BTC" if isinstance(best_pred.get('orderbook_depth'), (int, float)) else f"   Orderbook Depth: {best_pred.get('orderbook_depth', 'N/A')}")
                print(f"   Order Flow: {best_pred.get('orderbook_imbalance', 0)*100:+.1f}%" if isinstance(best_pred.get('orderbook_imbalance'), (int, float)) else "   Order Flow: N/A")
                print(f"   Prediction Time: {best_pred.get('prediction_datetime', 'N/A')}")
                print(f"   Reason: {best_pred.get('reason', 'No reason')}")
                
                # Check if enhanced factors influenced the prediction
                reactive_factor = best_pred.get('reactive_factor', 'none')
                if reactive_factor == 'hyperliquid_volume':
                    print(f"   🎯 ENHANCED: Used Hyperliquid real-time volume data!")
                elif reactive_factor == 'volume_spike':
                    print(f"   📊 STANDARD: Used Yahoo historical volume data")
                
                print(f"   Mode: {prediction_analysis.get('prediction_mode', 'UNKNOWN')}")
        
        return signal
        
    except Exception as e:
        print(f"❌ Error testing enhanced predictions: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_enhanced_predictions()
    if result:
        print(f"\n✅ Enhanced RSI & Volume integration test completed")
        if result.get('should_trade', False):
            print(f"🎯 Trade signal generated with enhanced data!")
        else:
            print(f"📊 No trade signal - waiting for better conditions")
    else:
        print(f"\n❌ Enhanced integration test failed")