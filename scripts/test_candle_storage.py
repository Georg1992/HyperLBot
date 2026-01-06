#!/usr/bin/env python3
"""
Test Candle Storage Database
Verifies that the candle storage database is working correctly
"""

import sys
import os
import sqlite3
from datetime import datetime

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger
from core.services.candle_storage import CandleStorage


def test_database_integrity(storage):
    """Test database integrity and data quality"""
    logger.info("🔍 Testing database integrity...")
    
    # Get database stats
    candle_count = storage.get_candle_count()
    first_timestamp = storage.get_first_timestamp()
    last_timestamp = storage.get_last_timestamp()
    
    if candle_count == 0:
        logger.error("❌ Database is empty")
        return False
    
    logger.info(f"✅ Database has {candle_count:,} candles")
    
    if first_timestamp and last_timestamp:
        first_date = datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        last_date = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        time_span = (last_timestamp - first_timestamp) / (365 * 24 * 3600)
        
        logger.info(f"✅ First candle: {first_date}")
        logger.info(f"✅ Last candle: {last_date}")
        logger.info(f"✅ Time span: {time_span:.2f} years")
        
        # Verify time span is reasonable (should be around 5 years)
        if time_span < 4.5 or time_span > 5.5:
            logger.warning(f"⚠️ Time span is {time_span:.2f} years (expected ~5 years)")
    else:
        logger.error("❌ Failed to get timestamp range")
        return False
    
    # Test querying candles
    logger.info("🔍 Testing candle queries...")
    
    # Test get_candles_by_count
    recent_candles = storage.get_candles_by_count(10)
    if len(recent_candles) != 10:
        logger.error(f"❌ Expected 10 candles, got {len(recent_candles)}")
        return False
    logger.info(f"✅ Successfully retrieved {len(recent_candles)} recent candles")
    
    # Verify candle structure
    sample_candle = recent_candles[0]
    required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing_fields = [field for field in required_fields if field not in sample_candle]
    if missing_fields:
        logger.error(f"❌ Missing required fields: {missing_fields}")
        return False
    logger.info("✅ Candle structure is valid")
    
    # Verify timestamps are in order
    timestamps = [c['timestamp'] for c in recent_candles]
    if timestamps != sorted(timestamps):
        logger.error("❌ Candles are not in chronological order")
        return False
    logger.info("✅ Candles are in chronological order")
    
    # Test get_candles_by_range
    test_start = last_timestamp - (24 * 3600)  # Last 24 hours
    test_end = last_timestamp
    range_candles = storage.get_candles_by_range(test_start, test_end)
    expected_count = 24 * 60 / 5  # 288 candles per day (5-minute intervals)
    if len(range_candles) < expected_count * 0.9:  # Allow 10% tolerance
        logger.warning(f"⚠️ Expected ~{expected_count} candles for 24h, got {len(range_candles)}")
    else:
        logger.info(f"✅ Successfully retrieved {len(range_candles)} candles for 24h range")
    
    # Verify no duplicate timestamps
    conn = sqlite3.connect(storage.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, COUNT(*) as count
        FROM candles_5m
        GROUP BY timestamp
        HAVING count > 1
    """)
    duplicates = cursor.fetchall()
    conn.close()
    
    if duplicates:
        logger.error(f"❌ Found {len(duplicates)} duplicate timestamps")
        return False
    logger.info("✅ No duplicate timestamps found")
    
    # Verify data quality (no null or zero values where they shouldn't be)
    conn = sqlite3.connect(storage.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM candles_5m 
        WHERE open = 0 OR high = 0 OR low = 0 OR close = 0 OR volume = 0
    """)
    invalid_candles = cursor.fetchone()[0]
    conn.close()
    
    if invalid_candles > 0:
        logger.warning(f"⚠️ Found {invalid_candles} candles with zero values (might be valid for very old data)")
    else:
        logger.info("✅ All candles have valid OHLCV data")
    
    return True


def test_update_functionality(storage):
    """Test that update functionality works"""
    logger.info("🔍 Testing update functionality...")
    
    # Get current state
    before_count = storage.get_candle_count()
    before_last = storage.get_last_timestamp()
    
    logger.info(f"📊 Before update: {before_count:,} candles, last: {datetime.fromtimestamp(before_last).strftime('%Y-%m-%d %H:%M:%S') if before_last else 'N/A'}")
    
    # Run backfill
    try:
        storage.backfill_missing_candles()
    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
        return False
    
    # Get updated state
    after_count = storage.get_candle_count()
    after_last = storage.get_last_timestamp()
    
    logger.info(f"📊 After update: {after_count:,} candles, last: {datetime.fromtimestamp(after_last).strftime('%Y-%m-%d %H:%M:%S') if after_last else 'N/A'}")
    
    # Verify update worked
    if after_last and before_last:
        if after_last >= before_last:
            logger.info("✅ Database was updated successfully")
            if after_last > before_last:
                logger.info(f"✅ Added candles from {datetime.fromtimestamp(before_last).strftime('%Y-%m-%d %H:%M:%S')} to {datetime.fromtimestamp(after_last).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.error("❌ Last timestamp went backwards (shouldn't happen)")
            return False
    else:
        logger.error("❌ Failed to get timestamps after update")
        return False
    
    return True


def main():
    """Run all tests"""
    logger.info("🧪 Starting candle storage tests...")
    
    try:
        # Initialize storage
        storage = CandleStorage(symbol="BTC")
        
        # Test 1: Database integrity
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Database Integrity")
        logger.info("="*60)
        if not test_database_integrity(storage):
            logger.error("❌ Database integrity test failed")
            sys.exit(1)
        
        # Test 2: Update functionality
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Update Functionality")
        logger.info("="*60)
        if not test_update_functionality(storage):
            logger.error("❌ Update functionality test failed")
            sys.exit(1)
        
        logger.info("\n" + "="*60)
        logger.info("✅ All tests passed!")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

