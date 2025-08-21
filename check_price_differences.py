#!/usr/bin/env python3
"""
Real-time Price Difference Checker
Compares BTC/USD prices between Hyperliquid and Yahoo Finance APIs
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

def check_price_differences():
    """Check real-time price differences between Hyperliquid and Yahoo Finance"""
    
    logger.info("🔍 Checking Real-time Price Differences")
    logger.info("=" * 60)
    
    # Initialize APIs
    config = TradingConfig()
    hyperliquid_api = HyperliquidAPI(config.WALLET_ADDRESS, config.WALLET_PRIVATE_KEY)
    yahoo_fetcher = YahooDataFetcher()
    
    # Test connections
    logger.info("🔌 Testing API connections...")
    
    # Test Yahoo Finance
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
    
    logger.info("\n📊 Starting real-time price comparison...")
    logger.info("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get Yahoo Finance price
            yahoo_price = yahoo_fetcher.get_current_price("BTC")
            
            # Get Hyperliquid price
            try:
                market_data = hyperliquid_api.get_market_data("BTC")
                if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                    bids = market_data['levels'][0]
                    asks = market_data['levels'][1]
                    
                    if bids and asks:
                        best_bid = float(bids[0]['px'])
                        best_ask = float(asks[0]['px'])
                        hyperliquid_price = (best_bid + best_ask) / 2
                    else:
                        hyperliquid_price = None
                else:
                    hyperliquid_price = None
            except Exception as e:
                hyperliquid_price = None
                logger.error(f"❌ Hyperliquid price fetch error: {e}")
            
            # Calculate difference if both prices available
            if yahoo_price and hyperliquid_price:
                difference = hyperliquid_price - yahoo_price
                difference_pct = (difference / yahoo_price) * 100
                
                # Determine status
                if abs(difference_pct) < 0.1:
                    status = "✅ EXCELLENT"
                elif abs(difference_pct) < 0.5:
                    status = "⚠️ GOOD"
                elif abs(difference_pct) < 1.0:
                    status = "⚠️ MODERATE"
                else:
                    status = "❌ HIGH"
                
                # Color coding for difference
                if abs(difference_pct) < 0.1:
                    diff_color = "🟢"
                elif abs(difference_pct) < 0.5:
                    diff_color = "🟡"
                else:
                    diff_color = "🔴"
                
                print(f"[{current_time}] {diff_color} {status}")
                print(f"   Yahoo Finance: ${yahoo_price:,.2f}")
                print(f"   Hyperliquid:   ${hyperliquid_price:,.2f}")
                print(f"   Difference:    ${difference:,.2f} ({difference_pct:+.3f}%)")
                print(f"   Spread:        ${best_ask - best_bid:,.2f}")
                print("-" * 60)
                
            else:
                print(f"[{current_time}] ❌ Price fetch failed")
                if yahoo_price:
                    print(f"   Yahoo Finance: ${yahoo_price:,.2f}")
                else:
                    print(f"   Yahoo Finance: ❌ Failed")
                
                if hyperliquid_price:
                    print(f"   Hyperliquid:   ${hyperliquid_price:,.2f}")
                else:
                    print(f"   Hyperliquid:   ❌ Failed")
                print("-" * 60)
            
            # Wait 5 seconds before next check
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Price comparison stopped by user")
        logger.info("📊 Summary:")
        logger.info("   • Yahoo Finance: Real-time BTC-USD spot price")
        logger.info("   • Hyperliquid: BTC/USD perpetual futures price")
        logger.info("   • Small differences are normal due to:")
        logger.info("     - Spot vs Futures pricing")
        logger.info("     - Different market makers")
        logger.info("     - Funding rate effects")
        logger.info("     - Market microstructure")

def main():
    """Main function"""
    logger.info("🚀 Starting Real-time Price Difference Checker")
    logger.info("This will compare BTC/USD prices between:")
    logger.info("   • Yahoo Finance (Spot)")
    logger.info("   • Hyperliquid (Perpetual Futures)")
    logger.info("=" * 60)
    
    check_price_differences()

if __name__ == "__main__":
    main()
