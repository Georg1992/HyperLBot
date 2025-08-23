#!/usr/bin/env python3
"""
Debug Trading Conditions
Check why the bot isn't executing trades by analyzing all conditions step by step
"""

import sys
import os
import time
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_all_trading_conditions():
    """Debug all conditions that might prevent trading"""
    try:
        logger.info("🔍 DEBUGGING TRADING CONDITIONS")
        logger.info("=" * 60)
        
        from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot
        
        # Initialize bot
        bot = YahooHyperliquidPaperTradingBot(initial_balance=120, strategy_name="low_volatility")
        
        # 1. CHECK API CONNECTIVITY
        logger.info("📡 1. CHECKING API CONNECTIVITY:")
        hyperliquid_price = bot.get_hyperliquid_price()
        if hyperliquid_price:
            logger.success(f"   ✅ Hyperliquid Price: ${hyperliquid_price:,.2f}")
        else:
            logger.error("   ❌ Failed to get Hyperliquid price")
            return False
        
        # 2. CHECK YAHOO FINANCE ANALYSIS
        logger.info("\n📊 2. CHECKING YAHOO FINANCE ANALYSIS:")
        binance_analysis = bot.yahoo_fetcher.get_market_analysis("BTC", hyperliquid_price=hyperliquid_price)
        if binance_analysis and "error" not in binance_analysis:
            logger.success("   ✅ Yahoo Finance analysis available")
            trend_5m = binance_analysis.get("5m", {}).get("trend", {}).get("trend", "UNKNOWN")
            trend_1h = binance_analysis.get("1h", {}).get("trend", {}).get("trend", "UNKNOWN")
            logger.info(f"   📈 5m Trend: {trend_5m}")
            logger.info(f"   📈 1h Trend: {trend_1h}")
        else:
            logger.error("   ❌ Failed to get Yahoo Finance analysis")
            return False
        
        # 3. CHECK TIME INTERVAL
        logger.info("\n⏰ 3. CHECKING TIME INTERVAL:")
        current_time = time.time()
        min_interval = bot.strategy_config["min_interval"]
        time_since_last = current_time - bot.last_trade_time
        if time_since_last >= min_interval:
            logger.success(f"   ✅ Time interval OK: {time_since_last:.1f}s >= {min_interval}s")
        else:
            logger.warning(f"   ⚠️ Too soon since last trade: {time_since_last:.1f}s < {min_interval}s")
        
        # 4. CHECK VARIABILITY CONDITIONS
        logger.info("\n📊 4. CHECKING VARIABILITY CONDITIONS:")
        from strategies.variability_analyzer import VariabilityAnalyzer
        
        variability_analyzer = VariabilityAnalyzer()
        
        # Add some sample price data if empty
        if len(variability_analyzer.price_history) == 0:
            logger.info("   📈 Adding sample price data...")
            for i in range(50):
                sample_price = hyperliquid_price + (i * 0.1)  # Add some variation
                variability_analyzer.add_price_data(sample_price, volume=100.0)
        
        variability_decision = variability_analyzer.should_trade_based_on_variability(0.5)
        
        logger.info(f"   📊 Should Trade: {variability_decision['should_trade']}")
        logger.info(f"   📊 Reason: {variability_decision['reason']}")
        
        if variability_decision.get("analysis"):
            analysis = variability_decision["analysis"]
            logger.info(f"   📊 Market Condition: {analysis.get('market_condition', 'UNKNOWN')}")
            logger.info(f"   📊 Trading Recommendation: {analysis.get('trading_recommendation', 'UNKNOWN')}")
            logger.info(f"   📊 Variability Score: {analysis.get('current_variability_score', 0):.3f}")
            logger.info(f"   📊 Confidence Score: {analysis.get('confidence_score', 0):.3f}")
        
        # 5. CHECK FULL SIGNAL GENERATION
        logger.info("\n🎯 5. CHECKING FULL SIGNAL GENERATION:")
        signal = bot.should_trade(hyperliquid_price, binance_analysis)
        
        logger.info(f"   🎯 Should Trade: {signal.get('should_trade', False)}")
        logger.info(f"   🎯 Reason: {signal.get('reason', 'Unknown')}")
        
        if signal.get("should_trade"):
            logger.success("   ✅ SIGNAL GENERATED - Bot should trade!")
            logger.info(f"   📊 Side: {signal.get('side', 'UNKNOWN')}")
            logger.info(f"   📊 Target: ${signal.get('target', 0):,.2f}")
            logger.info(f"   📊 Confidence: {signal.get('quality_evaluation', {}).get('confidence_level', 'UNKNOWN')}")
        else:
            logger.error("   ❌ NO SIGNAL - This is why bot isn't trading!")
        
        # 6. CHECK ULTIMATE PRESSURE (NEW SYSTEM)
        logger.info("\n🎯 6. CHECKING ULTIMATE PRESSURE INDICATOR:")
        try:
            pressure_data = bot.hyperliquid_api.get_ultimate_pressure("BTC")
            if pressure_data.get("status") == "success":
                direction = pressure_data.get("direction", "UNKNOWN")
                score = pressure_data.get("pressure_score", 0)
                confidence = pressure_data.get("confidence", "0%")
                
                logger.success(f"   ✅ Ultimate Pressure: {direction} ({score:+.1f}) - {confidence}")
                
                # Suggest if this would be better for trading
                confidence_pct = int(confidence.replace('%', '')) if confidence != "0%" else 0
                if direction in ["STRONG_BUY", "BUY"] and confidence_pct >= 70:
                    logger.success("   🚀 STRONG BUY SIGNAL - Consider using Ultimate Pressure instead!")
                elif direction in ["STRONG_SELL", "SELL"] and confidence_pct >= 70:
                    logger.success("   🚀 STRONG SELL SIGNAL - Consider using Ultimate Pressure instead!")
                else:
                    logger.info(f"   ⚪ Neutral/Low confidence pressure signal")
            else:
                logger.warning("   ⚠️ Ultimate Pressure indicator failed")
        except Exception as e:
            logger.warning(f"   ⚠️ Ultimate Pressure error: {e}")
        
        # 7. SUMMARY AND RECOMMENDATIONS
        logger.info("\n💡 7. RECOMMENDATIONS:")
        logger.info("=" * 60)
        
        if not signal.get("should_trade"):
            reason = signal.get("reason", "Unknown")
            logger.error(f"❌ MAIN ISSUE: {reason}")
            
            if "variability" in reason.lower() or "poor trading conditions" in reason.lower():
                logger.warning("💡 SOLUTION 1: Variability thresholds may be too conservative")
                logger.warning("   • Current thresholds: optimal=0.7, good=0.5, poor=0.2")
                logger.warning("   • Consider lowering thresholds or using Ultimate Pressure instead")
            
            if "no valid prediction" in reason.lower():
                logger.warning("💡 SOLUTION 2: Prediction engine may need adjustment")
                logger.warning("   • Check trend detection sensitivity")
                logger.warning("   • Verify historical data availability")
            
            if "trade quality check failed" in reason.lower():
                logger.warning("💡 SOLUTION 3: Trade quality filters may be too strict")
                logger.warning("   • Check trade manager conditions")
                logger.warning("   • Review quality evaluation criteria")
            
            logger.info("\n🚀 ALTERNATIVE: Use Ultimate Pressure Indicator")
            logger.info("   • More accurate buy/sell signals")
            logger.info("   • Updates every 1-2 seconds")
            logger.info("   • 7 different signal types combined")
            logger.info("   • Professional-grade accuracy")
        else:
            logger.success("✅ ALL CONDITIONS MET - Bot should be trading!")
            logger.success("   Check if bot is actually running in trading mode")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("🚀 Trading Conditions Debugger")
    print()
    
    success = debug_all_trading_conditions()
    
    if success:
        logger.info("\n✅ Debug completed successfully!")
    else:
        logger.error("\n❌ Debug encountered errors")
    
    print()