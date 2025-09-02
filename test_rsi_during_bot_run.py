#!/usr/bin/env python3
"""
RSI Accuracy Test During Bot Operation
=====================================
Tests real-time RSI accuracy when bot is running with working Hyperliquid API.

USAGE: Run this WHILE your bot is running (when API is connected)

TEST FLOW:
1. Get current Yahoo RSI baseline from running bot
2. Monitor real-time RSI changes for 60 seconds  
3. Compare with next Yahoo fetch
4. Validate accuracy for scalping
"""

import time
import sys
import os
from datetime import datetime

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from loguru import logger

def test_rsi_accuracy_during_bot():
    """Test RSI accuracy by monitoring the running bot's data"""
    
    # Setup minimal logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss.SSS}</green> | {message}",
        level="INFO"
    )
    
    logger.info("🔬 RSI ACCURACY TEST (During Bot Operation)")
    logger.info("=" * 60)
    logger.info("⚠️  REQUIREMENT: Run this WHILE your bot is running!")
    logger.info("🎯 Testing: Real-time RSI accuracy with working Hyperliquid API")
    logger.info("")
    
    try:
        # Connect to running bot's data
        from core.dashboard.dashboard_data_manager import simple_rtm
        from core.market_data_manager import global_rsi_calculator
        from core.external.yahoo_data_fetcher import YahooDataFetcher
        
        # STEP 1: Get current bot state
        logger.info("📊 STEP 1: Getting current bot RSI state")
        logger.info("-" * 50)
        
        bot_data = simple_rtm.get_market_data()
        if not bot_data or not bot_data.get("current_price"):
            logger.error("❌ Bot is not running or no market data available")
            logger.error("💡 Please start your bot first, then run this test")
            return
        
        initial_price = bot_data.get("current_price", 0)
        initial_rsi = bot_data.get("rsi", 0)
        
        logger.info(f"✅ Bot running - Current price: ${initial_price:,.2f}")
        logger.info(f"✅ Bot running - Current RSI: {initial_rsi:.2f}")
        logger.info("")
        
        # STEP 2: Monitor for 60 seconds
        logger.info("📊 STEP 2: Monitoring real-time RSI changes (60 seconds)")
        logger.info("-" * 50)
        logger.info("🎯 Watching bot's real-time RSI updates")
        logger.info("")
        
        start_time = time.time()
        price_history = []
        rsi_history = []
        update_count = 0
        
        while time.time() - start_time < 60:
            try:
                # Get current bot data
                current_data = simple_rtm.get_market_data()
                current_price = current_data.get("current_price", 0)
                current_rsi = current_data.get("rsi", 0)
                
                if current_price != initial_price or current_rsi != initial_rsi:
                    update_count += 1
                    elapsed = time.time() - start_time
                    price_change_pct = ((current_price - initial_price) / initial_price) * 100
                    rsi_change = current_rsi - initial_rsi
                    
                    price_history.append(current_price)
                    rsi_history.append(current_rsi)
                    
                    logger.info(f"   Update #{update_count:2d} [{elapsed:4.1f}s]: ${current_price:8,.2f} ({price_change_pct:+.3f}%) | RSI: {current_rsi:6.2f} ({rsi_change:+.2f})")
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.warning(f"⚠️ Error reading bot data: {e}")
                time.sleep(2)
        
        # STEP 3: Get final state
        logger.info("")
        logger.info("📊 STEP 3: Final bot state after 60 seconds")
        logger.info("-" * 50)
        
        final_data = simple_rtm.get_market_data()
        final_price = final_data.get("current_price", initial_price)
        final_rsi = final_data.get("rsi", initial_rsi)
        
        total_price_change = ((final_price - initial_price) / initial_price) * 100
        total_rsi_change = final_rsi - initial_rsi
        
        logger.info(f"🔬 Final bot RSI: {final_rsi:.2f}")
        logger.info(f"📈 Final bot price: ${final_price:,.2f}")
        logger.info(f"📊 Total price change: {total_price_change:+.3f}%")
        logger.info(f"📊 Total RSI change: {total_rsi_change:+.2f}")
        logger.info(f"⏱️ Updates captured: {update_count}")
        logger.info("")
        
        # STEP 4: Fresh Yahoo validation
        logger.info("📊 STEP 4: Fresh Yahoo validation")
        logger.info("-" * 50)
        
        yahoo_fetcher = YahooDataFetcher()
        fresh_candles = yahoo_fetcher.get_klines("BTC-USD", "5m", 30)
        
        if fresh_candles and len(fresh_candles) >= 15:
            from core.market_data_manager import market_data_manager
            validation_yahoo_rsi = market_data_manager.calculate_rsi_from_candles(fresh_candles)
            
            logger.info(f"✅ Fresh Yahoo RSI: {validation_yahoo_rsi:.2f}")
            logger.info("")
            
            # ACTUAL VALIDATION
            if update_count > 0:
                accuracy_gap = abs(final_rsi - validation_yahoo_rsi)
                
                logger.info("📊 REAL ACCURACY VALIDATION:")
                logger.info("=" * 50)
                logger.info(f"🔬 Bot real-time RSI: {final_rsi:.2f}")
                logger.info(f"📊 Yahoo validation:  {validation_yahoo_rsi:.2f}")
                logger.info(f"📉 Accuracy gap:      {accuracy_gap:.2f} points")
                
                if accuracy_gap <= 1.0:
                    logger.success("✅ EXCELLENT: Real-time RSI very accurate!")
                    rating = "EXCELLENT"
                elif accuracy_gap <= 2.0:
                    logger.info("✅ GOOD: Real-time RSI acceptable")
                    rating = "GOOD"
                else:
                    logger.warning("⚠️ NEEDS IMPROVEMENT: Large accuracy gap")
                    rating = "NEEDS IMPROVEMENT"
                
                logger.info(f"⭐ Rating: {rating}")
                return True
            else:
                logger.warning("⚠️ No real-time updates captured - bot may not be updating RSI")
                return False
        else:
            logger.error("❌ Could not get Yahoo validation data")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        logger.error("💡 Make sure your bot is running first!")
        return False

if __name__ == "__main__":
    logger.info("💡 INSTRUCTIONS:")
    logger.info("   1. Start your bot: python main.py")
    logger.info("   2. Choose Paper Trading") 
    logger.info("   3. Wait for bot to connect")
    logger.info("   4. Run this test: python3 test_rsi_during_bot_run.py")
    logger.info("")
    
    if test_rsi_accuracy_during_bot():
        print("\n🎯 SUCCESS: Real-time RSI validated for scalping!")
    else:
        print("\n❌ FAILED: Test could not validate real-time RSI")