#!/usr/bin/env python3
"""
Test script to start the bot directly without user input
"""

import time
import signal
import sys
from core.bot.trading_bot import YahooHyperliquidPaperTradingBot
from loguru import logger

def signal_handler(signum, frame):
    """Handle shutdown signal"""
    logger.info("🛑 Shutdown signal received, stopping bot...")
    sys.exit(0)

def test_bot_start():
    """Test starting the bot directly"""
    try:
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("🚀 Starting bot test...")
        
        # Initialize bot with small balance and short session
        from core.constants import MagicNumbers
    bot = YahooHyperliquidPaperTradingBot(initial_balance=MagicNumbers.TEST_BALANCE)
        
        # Connect to APIs
        if not bot.connect():
            logger.error("❌ Failed to connect to APIs")
            return
        
        # Start a short trading session (2 trades max, 3 second intervals)
        logger.info("🤖 Starting short trading session...")
        bot.run_yahoo_hyperliquid_paper_trading(
            max_trades=2,      # Only 2 trades
            check_interval=3   # Check every 3 seconds
        )
        
        logger.info("✅ Bot test completed successfully")
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Bot test failed: {e}")

if __name__ == "__main__":
    test_bot_start()
