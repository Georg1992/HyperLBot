#!/usr/bin/env python3
"""
Test Aggregations
Verifies that all timeframe aggregations work correctly
"""

import sys
import os

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger
from core.services.historical_data_service import HistoricalDataService


def test_aggregations():
    """Test all timeframe aggregations"""
    logger.info("🧪 Testing aggregations...")
    
    try:
        h = HistoricalDataService()
        
        # Test 5m candles (direct from database)
        logger.info("\n📊 Testing 5m candles...")
        candles_5m = h.get_historical_candles("BTC", "5m", 30)
        logger.info(f"✅ Got {len(candles_5m)} 5m candles")
        if len(candles_5m) != 30:
            logger.error(f"❌ Expected 30 5m candles, got {len(candles_5m)}")
            return False
        
        # Test 15m candles (aggregated from 5m)
        logger.info("\n📊 Testing 15m candles...")
        candles_15m = h.get_historical_candles("BTC", "15m", 30)
        logger.info(f"✅ Got {len(candles_15m)} 15m candles")
        if len(candles_15m) != 30:
            logger.error(f"❌ Expected 30 15m candles, got {len(candles_15m)}")
            return False
        
        # Test 1h candles (aggregated from 5m)
        logger.info("\n📊 Testing 1h candles...")
        candles_1h = h.get_historical_candles("BTC", "1h", 30)
        logger.info(f"✅ Got {len(candles_1h)} 1h candles")
        if len(candles_1h) != 30:
            logger.error(f"❌ Expected 30 1h candles, got {len(candles_1h)}")
            return False
        
        # Test 1d candles (aggregated from 5m)
        logger.info("\n📊 Testing 1d candles...")
        candles_1d = h.get_historical_candles("BTC", "1d", 30)
        logger.info(f"✅ Got {len(candles_1d)} 1d candles")
        if len(candles_1d) != 30:
            logger.error(f"❌ Expected 30 1d candles, got {len(candles_1d)}")
            return False
        
        # Verify candle structure
        logger.info("\n🔍 Verifying candle structure...")
        sample = candles_1d[0]
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [f for f in required_fields if f not in sample]
        if missing:
            logger.error(f"❌ Missing fields: {missing}")
            return False
        logger.info("✅ Candle structure is valid")
        
        # Verify data quality
        logger.info("\n🔍 Verifying data quality...")
        for tf, candles in [("15m", candles_15m), ("1h", candles_1h), ("1d", candles_1d)]:
            for c in candles:
                if c['high'] < c['low']:
                    logger.error(f"❌ Invalid {tf} candle: high < low")
                    return False
                if c['open'] < 0 or c['high'] < 0 or c['low'] < 0 or c['close'] < 0:
                    logger.error(f"❌ Invalid {tf} candle: negative values")
                    return False
        logger.info("✅ All aggregations have valid data")
        
        logger.info("\n" + "="*60)
        logger.info("✅ All aggregation tests PASSED")
        logger.info("="*60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Aggregation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_aggregations()
    sys.exit(0 if success else 1)
