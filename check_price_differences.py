#!/usr/bin/env python3
"""
Real-time Price Validation Checker
Validates that Hyperliquid is the exclusive source for real-time BTC/USD pricing
Yahoo Finance is used only for historical data and analysis
"""

import time
import json
from datetime import datetime
from loguru import logger
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.hyperliquid_api import HyperliquidAPI
from data.yahoo_data_fetcher import YahooDataFetcher
from core.config import TradingConfig

def validate_price_architecture():
    """Validate that Hyperliquid is the exclusive source for real-time pricing"""
    
    logger.info("🔍 Validating Price Architecture")
    logger.info("=" * 60)
    logger.info("📊 Expected Architecture:")
    logger.info("   • Hyperliquid: EXCLUSIVE real-time pricing source")
    logger.info("   • Yahoo Finance: Historical data and analysis only")
    logger.info("=" * 60)
    
    # Initialize APIs
    config = TradingConfig()
    hyperliquid_api = HyperliquidAPI(config.WALLET_ADDRESS, config.WALLET_PRIVATE_KEY)
    yahoo_fetcher = YahooDataFetcher()
    
    # Test connections
    logger.info("🔌 Testing API connections...")
    
    # Test Yahoo Finance (historical data only)
    if not yahoo_fetcher.test_connection():
        logger.error("❌ Yahoo Finance connection failed")
        return
    
    # Test Hyperliquid
    try:
        market_data = hyperliquid_api.get_market_data("BTC")
        if not market_data:
            logger.error("❌ Hyperliquid connection failed")
            return
        logger.success("✅ Both APIs connected successfully")
    except Exception as e:
        logger.error(f"❌ Hyperliquid connection error: {e}")
        return
    
    logger.info("\n📊 Starting price validation...")
    logger.info("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get Hyperliquid price (EXCLUSIVE real-time source)
            try:
                market_data = hyperliquid_api.get_market_data("BTC")
                if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                    bids = market_data['levels'][0]
                    asks = market_data['levels'][1]
                    
                    if bids and asks:
                        best_bid = float(bids[0]['px'])
                        best_ask = float(asks[0]['px'])
                        hyperliquid_price = (best_bid + best_ask) / 2
                        spread = best_ask - best_bid
                    else:
                        hyperliquid_price = None
                        spread = None
                else:
                    hyperliquid_price = None
                    spread = None
            except Exception as e:
                hyperliquid_price = None
                spread = None
                logger.error(f"❌ Hyperliquid price fetch error: {e}")
            
            # Get Yahoo Finance historical analysis (NO real-time price)
            try:
                yahoo_analysis = yahoo_fetcher.get_market_analysis("BTC", hyperliquid_price=hyperliquid_price)
                if "error" not in yahoo_analysis:
                    yahoo_last_close = yahoo_analysis.get("current_price", 0)  # This should be Hyperliquid price
                    yahoo_trend = yahoo_analysis.get("trend_5m", {}).get("trend", "UNKNOWN")
                    yahoo_condition = yahoo_analysis.get("market_condition", "UNKNOWN")
                else:
                    yahoo_last_close = 0
                    yahoo_trend = "ERROR"
                    yahoo_condition = "ERROR"
            except Exception as e:
                yahoo_last_close = 0
                yahoo_trend = "ERROR"
                yahoo_condition = "ERROR"
                logger.error(f"❌ Yahoo analysis error: {e}")
            
            # Display results
            if hyperliquid_price:
                logger.info(f"⏰ {current_time}")
                logger.info(f"💰 Hyperliquid Price: ${hyperliquid_price:,.2f} (Spread: ${spread:,.2f})")
                logger.info(f"📊 Yahoo Analysis: ${yahoo_last_close:,.2f} | Trend: {yahoo_trend} | Condition: {yahoo_condition}")
                
                # Validate architecture
                if abs(hyperliquid_price - yahoo_last_close) < 0.01:  # Should be identical
                    logger.success("✅ Architecture Valid: Yahoo using Hyperliquid price for analysis")
                else:
                    logger.warning("⚠️ Architecture Issue: Price mismatch detected")
                
                logger.info("-" * 50)
            else:
                logger.warning(f"⚠️ {current_time} - No Hyperliquid price available")
            
            # Wait before next check
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Price validation stopped by user")
    except Exception as e:
        logger.error(f"❌ Error in price validation: {e}")


if __name__ == "__main__":
    validate_price_architecture()
