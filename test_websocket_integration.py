#!/usr/bin/env python3
"""
Test script to verify WebSocket integration and dashboard updates
"""

import time
import signal
import sys
from strategies.hybrid_paper_trading_bot import YahooHyperliquidPaperTradingBot
from loguru import logger

def signal_handler(signum, frame):
    """Handle shutdown signal"""
    logger.info("🛑 Shutdown signal received, stopping test...")
    sys.exit(0)

def test_websocket_integration():
    """Test WebSocket integration and dashboard updates"""
    try:
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("🚀 Testing WebSocket integration...")
        
        # Initialize bot with small balance
        bot = YahooHyperliquidPaperTradingBot(initial_balance=100.0)
        
        # Connect to APIs
        if not bot.connect():
            logger.error("❌ Failed to connect to APIs")
            return
        
        logger.info("✅ Bot initialized and connected successfully")
        logger.info("📡 WebSocket should be providing real-time price updates")
        logger.info("🔄 Dashboard should be receiving updates via SimpleRTM")
        
        # Test price updates for 10 seconds
        logger.info("⏳ Testing price updates for 10 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 10:
            try:
                # Get current price from WebSocket
                price = bot.get_hyperliquid_price()
                if price:
                    logger.info(f"💰 Current price: ${price:,.2f}")
                else:
                    logger.warning("⚠️ No price data available")
                
                time.sleep(2)  # Check every 2 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Error getting price: {e}")
                time.sleep(2)
        
        logger.info("✅ WebSocket integration test completed")
        logger.info("📊 Check the dashboard to see if values are updating properly")
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_websocket_integration()
