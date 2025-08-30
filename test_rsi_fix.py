#!/usr/bin/env python3
"""
Test the RSI fix for realistic values
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.analysis.real_time.rsi_calculator import real_time_rsi_calculator
from core.external.yahoo_data_fetcher import YahooDataFetcher
from loguru import logger

def test_rsi_realistic_values():
    """Test that RSI produces realistic values"""
    logger.info("🧪 Testing RSI fix for realistic values")
    
    # Initialize Yahoo fetcher
    yahoo_fetcher = YahooDataFetcher()
    
    # Test connection
    if not yahoo_fetcher.test_connection():
        logger.error("❌ Cannot connect to Yahoo Finance")
        return False
    
    # Get Yahoo 5-minute candles
    logger.info("📊 Fetching Yahoo 5-minute candles...")
    candles_5m = yahoo_fetcher.get_5m_klines("BTC", 20)
    
    if not candles_5m or len(candles_5m) < 15:
        logger.error("❌ Not enough Yahoo data for testing")
        return False
    
    # Calculate RSI from Yahoo
    logger.info("📊 Calculating RSI from Yahoo data...")
    yahoo_rsi = yahoo_fetcher.calculate_rsi_from_candles(candles_5m)
    logger.info(f"📊 Yahoo RSI: {yahoo_rsi:.2f}")
    
    # Extract prices for initialization
    yahoo_prices = [c['close'] for c in candles_5m[-15:]]
    logger.info(f"📊 Yahoo prices: {len(yahoo_prices)} prices")
    logger.info(f"📊 Price range: ${min(yahoo_prices):.2f} - ${max(yahoo_prices):.2f}")
    
    # Calculate price volatility for reference
    price_volatility = max(yahoo_prices) - min(yahoo_prices)
    base_change = price_volatility / len(yahoo_prices)
    logger.info(f"📊 Price volatility: ${price_volatility:.2f}")
    logger.info(f"📊 Base change: ${base_change:.2f}")
    
    # Initialize RSI calculator
    logger.info("📊 Initializing RSI calculator with Yahoo data...")
    success = real_time_rsi_calculator.initialize_with_yahoo_rsi(yahoo_rsi, yahoo_prices)
    
    if not success:
        logger.error("❌ Failed to initialize RSI calculator")
        return False
    
    # Get initial RSI
    initial_rsi_data = real_time_rsi_calculator.get_rsi()
    logger.info(f"📊 Initial RSI: {initial_rsi_data['rsi']:.2f}")
    logger.info(f"📊 Initial avg_gain: {initial_rsi_data['avg_gain']:.6f}")
    logger.info(f"📊 Initial avg_loss: {initial_rsi_data['avg_loss']:.6f}")
    
    # Test with the problematic price change that caused 99.88
    last_price = yahoo_prices[-1]
    problematic_price = last_price + 108.86  # The change that caused 99.88
    
    logger.info(f"📊 Testing with problematic price change: ${last_price:.2f} -> ${problematic_price:.2f} (+${108.86:.2f})")
    
    updated = real_time_rsi_calculator.update_price(problematic_price)
    if updated:
        rsi_data = real_time_rsi_calculator.get_rsi()
        logger.info(f"📊 RSI after problematic change: {rsi_data['rsi']:.2f}")
        logger.info(f"📊 New avg_gain: {rsi_data['avg_gain']:.6f}")
        logger.info(f"📊 New avg_loss: {rsi_data['avg_loss']:.6f}")
        
        # Check if this is more realistic
        if rsi_data['rsi'] < 90:
            logger.success(f"✅ RSI fix successful! Value {rsi_data['rsi']:.2f} is much more realistic than 99.88")
        else:
            logger.warning(f"⚠️ RSI still high: {rsi_data['rsi']:.2f} - may need further adjustment")
    else:
        logger.error("❌ No RSI update")
    
    # Test with smaller price changes
    logger.info("📊 Testing with smaller price changes...")
    
    small_changes = [
        (last_price * 1.001, "0.1% increase"),
        (last_price * 0.999, "0.1% decrease"),
        (last_price * 1.005, "0.5% increase"),
        (last_price * 0.995, "0.5% decrease"),
    ]
    
    for new_price, description in small_changes:
        change = new_price - last_price
        logger.info(f"📊 Testing {description}: ${last_price:.2f} -> ${new_price:.2f} ({change:+.2f})")
        
        updated = real_time_rsi_calculator.update_price(new_price)
        if updated:
            rsi_data = real_time_rsi_calculator.get_rsi()
            logger.info(f"   RSI: {rsi_data['rsi']:.2f} | Trend: {rsi_data['trend']}")
        else:
            logger.warning("   No RSI update")
    
    logger.success("✅ RSI realistic value test completed!")
    return True

if __name__ == "__main__":
    test_rsi_realistic_values()
