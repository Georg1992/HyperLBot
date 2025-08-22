#!/usr/bin/env python3
"""
Test RSI Accuracy Script
Checks the current RSI calculation and compares with dashboard values
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import TradingConfig
from core.hyperliquid_api import HyperliquidAPI
from data.yahoo_data_fetcher import YahooDataFetcher
from loguru import logger

def test_rsi_accuracy():
    """Test RSI calculation accuracy"""
    try:
        logger.info("🔍 Testing RSI calculation accuracy...")
        
        # Initialize APIs
        config = TradingConfig()
        api = HyperliquidAPI(config.WALLET_ADDRESS, config.WALLET_PRIVATE_KEY)
        fetcher = YahooDataFetcher()
        
        # Get fresh Yahoo data
        logger.info("📊 Fetching fresh Yahoo candlestick data...")
        candles = fetcher.get_klines("BTC", "5m", 30)
        
        if not candles or len(candles) < 25:
            logger.error("❌ Insufficient candle data for RSI calculation")
            return False
        
        logger.info(f"✅ Got {len(candles)} candles from Yahoo Finance")
        
        # Calculate RSI using our method
        logger.info("🧮 Calculating RSI using our method...")
        rsi_result = api.calculate_rsi_from_yahoo_data(candles, periods=20)
        our_rsi = rsi_result.get("rsi")
        
        logger.info(f"📈 Our RSI calculation: {our_rsi:.1f}")
        logger.info(f"📊 Calculation method: {rsi_result.get('calculation_method', 'unknown')}")
        logger.info(f"📊 Periods used: {rsi_result.get('periods_used', 'unknown')}")
        logger.info(f"📊 Current price: ${rsi_result.get('current_price', 0):,.2f}")
        
        # Get current Hyperliquid price for comparison
        logger.info("🔗 Getting current Hyperliquid price...")
        hyperliquid_price = api.get_current_price("BTC")
        if hyperliquid_price:
            logger.info(f"💰 Hyperliquid price: ${hyperliquid_price:,.2f}")
            
            # Calculate price difference
            if rsi_result.get("current_price"):
                price_diff = abs(hyperliquid_price - rsi_result.get("current_price"))
                price_diff_pct = (price_diff / hyperliquid_price) * 100
                logger.info(f"📊 Price difference: ${price_diff:.2f} ({price_diff_pct:.2f}%)")
        
        # Show recent candle data for debugging
        logger.info("📋 Recent candle data (last 5):")
        for i, candle in enumerate(candles[-5:]):
            logger.info(f"  Candle {i+1}: Open=${candle['open']:.2f}, Close=${candle['close']:.2f}, High=${candle['high']:.2f}, Low=${candle['low']:.2f}, Volume={candle['volume']}")
        
        # Check if RSI calculation looks reasonable
        if our_rsi:
            if our_rsi < 0 or our_rsi > 100:
                logger.warning(f"⚠️ RSI value {our_rsi:.1f} is outside normal range (0-100)")
            elif our_rsi > 70:
                logger.info(f"🔴 RSI {our_rsi:.1f} indicates overbought conditions")
            elif our_rsi < 30:
                logger.info(f"🟢 RSI {our_rsi:.1f} indicates oversold conditions")
            else:
                logger.info(f"⚪ RSI {our_rsi:.1f} indicates neutral conditions")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing RSI accuracy: {e}")
        return False

if __name__ == "__main__":
    logger.info("🧪 HyperLBot RSI Accuracy Test")
    success = test_rsi_accuracy()
    
    if success:
        logger.info("✅ RSI accuracy test completed successfully!")
    else:
        logger.error("💥 RSI accuracy test failed!")
        sys.exit(1)
