#!/usr/bin/env python3
"""
Check Database Integrity
Verifies that candle data is properly stored with valid timestamps and structure
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


def check_database_integrity():
    """Comprehensive database integrity check"""
    logger.info("🔍 Starting database integrity check...")
    
    try:
        storage = CandleStorage(symbol="BTC")
        
        # Get database stats
        candle_count = storage.get_candle_count()
        first_timestamp = storage.get_first_timestamp()
        last_timestamp = storage.get_last_timestamp()
        
        logger.info(f"📊 Database Statistics:")
        logger.info(f"   Total candles: {candle_count:,}")
        
        if not first_timestamp or not last_timestamp:
            logger.error("❌ Database is empty or corrupted - no timestamps found")
            return False
        
        first_date = datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        last_date = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        time_span = (last_timestamp - first_timestamp) / (365 * 24 * 3600)
        
        logger.info(f"   First candle: {first_date}")
        logger.info(f"   Last candle: {last_date}")
        logger.info(f"   Time span: {time_span:.2f} years")
        
        # Connect directly to database for detailed checks
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        
        # Check 1: All candles have timestamps
        logger.info("\n🔍 Check 1: Verifying all candles have timestamps...")
        cursor.execute("SELECT COUNT(*) FROM candles_5m WHERE timestamp IS NULL")
        null_timestamps = cursor.fetchone()[0]
        if null_timestamps > 0:
            logger.error(f"❌ Found {null_timestamps} candles with NULL timestamps")
            return False
        logger.info(f"✅ All {candle_count:,} candles have timestamps")
        
        # Check 2: No duplicate timestamps
        logger.info("\n🔍 Check 2: Checking for duplicate timestamps...")
        cursor.execute("""
            SELECT timestamp, COUNT(*) as count
            FROM candles_5m
            GROUP BY timestamp
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            logger.error(f"❌ Found {len(duplicates)} duplicate timestamps:")
            for ts, count in duplicates[:10]:  # Show first 10
                logger.error(f"   Timestamp {ts} appears {count} times")
            return False
        logger.info("✅ No duplicate timestamps found")
        
        # Check 3: Timestamps are in valid range (not zero, not future, not too old)
        logger.info("\n🔍 Check 3: Validating timestamp ranges...")
        current_time = datetime.now().timestamp()
        five_years_ago = current_time - (5 * 365 * 24 * 3600)
        ten_years_ago = current_time - (10 * 365 * 24 * 3600)
        
        cursor.execute("SELECT COUNT(*) FROM candles_5m WHERE timestamp <= 0")
        invalid_timestamps = cursor.fetchone()[0]
        if invalid_timestamps > 0:
            logger.error(f"❌ Found {invalid_timestamps} candles with invalid timestamps (<= 0)")
            return False
        
        cursor.execute("SELECT COUNT(*) FROM candles_5m WHERE timestamp > ?", (current_time + 3600,))
        future_timestamps = cursor.fetchone()[0]
        if future_timestamps > 0:
            logger.warning(f"⚠️ Found {future_timestamps} candles with future timestamps (> 1 hour ahead)")
        
        cursor.execute("SELECT COUNT(*) FROM candles_5m WHERE timestamp < ?", (ten_years_ago,))
        very_old_timestamps = cursor.fetchone()[0]
        if very_old_timestamps > 0:
            logger.warning(f"⚠️ Found {very_old_timestamps} candles older than 10 years (might be valid)")
        
        logger.info("✅ Timestamp ranges are valid")
        
        # Check 4: OHLCV data is valid (not all zeros, reasonable values)
        logger.info("\n🔍 Check 4: Validating OHLCV data...")
        cursor.execute("""
            SELECT COUNT(*) FROM candles_5m 
            WHERE open = 0 OR high = 0 OR low = 0 OR close = 0
        """)
        zero_values = cursor.fetchone()[0]
        if zero_values > 0:
            logger.warning(f"⚠️ Found {zero_values} candles with zero OHLC values (might be valid for very old data)")
        
        cursor.execute("""
            SELECT COUNT(*) FROM candles_5m 
            WHERE high < low OR open < 0 OR high < 0 OR low < 0 OR close < 0
        """)
        invalid_ohlc = cursor.fetchone()[0]
        if invalid_ohlc > 0:
            logger.error(f"❌ Found {invalid_ohlc} candles with invalid OHLC data (high < low or negative values)")
            return False
        
        cursor.execute("""
            SELECT COUNT(*) FROM candles_5m 
            WHERE open > high OR open < low OR close > high OR close < low
        """)
        out_of_range = cursor.fetchone()[0]
        if out_of_range > 0:
            logger.error(f"❌ Found {out_of_range} candles with OHLC values out of range")
            return False
        
        logger.info("✅ OHLCV data is valid")
        
        # Check 5: Timestamps are properly spaced (5-minute intervals)
        logger.info("\n🔍 Check 5: Checking timestamp spacing (5-minute intervals)...")
        cursor.execute("""
            SELECT timestamp 
            FROM candles_5m 
            ORDER BY timestamp 
            LIMIT 1000
        """)
        timestamps = [row[0] for row in cursor.fetchall()]
        
        if len(timestamps) > 1:
            gaps = []
            for i in range(1, len(timestamps)):
                gap = timestamps[i] - timestamps[i-1]
                gaps.append(gap)
            
            # Check if gaps are approximately 300 seconds (5 minutes)
            # Allow some tolerance for missing candles
            expected_gap = 300  # 5 minutes in seconds
            tolerance = 10  # 10 seconds tolerance
            
            invalid_gaps = [g for g in gaps if abs(g - expected_gap) > tolerance and g < expected_gap * 0.9]
            if invalid_gaps:
                logger.warning(f"⚠️ Found {len(invalid_gaps)} unexpected gaps in first 1000 candles")
                logger.warning(f"   Expected ~{expected_gap}s intervals, found gaps: {sorted(set(invalid_gaps))[:10]}")
            else:
                logger.info(f"✅ Timestamp spacing is correct (5-minute intervals)")
        
        # Check 6: Check for missing required fields
        logger.info("\n🔍 Check 6: Verifying all required fields are present...")
        cursor.execute("""
            SELECT COUNT(*) FROM candles_5m 
            WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL
        """)
        null_fields = cursor.fetchone()[0]
        if null_fields > 0:
            logger.error(f"❌ Found {null_fields} candles with NULL required fields")
            return False
        logger.info("✅ All required fields are present")
        
        # Check 7: Sample data quality check
        logger.info("\n🔍 Check 7: Sampling data quality...")
        cursor.execute("""
            SELECT timestamp, open, high, low, close, volume, trades_count
            FROM candles_5m
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        recent_candles = cursor.fetchall()
        
        logger.info("📊 Sample of 10 most recent candles:")
        for ts, o, h, l, c, v, tc in recent_candles:
            date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"   {date_str}: O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f} V={v:.2f} Trades={tc}")
        
        # Check 8: Verify chronological order
        logger.info("\n🔍 Check 8: Verifying chronological order...")
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT timestamp, 
                       LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp
                FROM candles_5m
            ) WHERE prev_timestamp IS NOT NULL AND timestamp < prev_timestamp
        """)
        out_of_order = cursor.fetchone()[0]
        if out_of_order > 0:
            logger.error(f"❌ Found {out_of_order} candles out of chronological order")
            return False
        logger.info("✅ All candles are in chronological order")
        
        # Check 9: Check for gaps in data
        logger.info("\n🔍 Check 9: Checking for significant data gaps...")
        cursor.execute("""
            SELECT 
                timestamp,
                LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp,
                timestamp - LAG(timestamp) OVER (ORDER BY timestamp) as gap
            FROM candles_5m
            WHERE timestamp > ?
            ORDER BY gap DESC
            LIMIT 10
        """, (five_years_ago,))
        large_gaps = cursor.fetchall()
        
        if large_gaps:
            logger.info("📊 Largest gaps in recent data (last 5 years):")
            for ts, prev_ts, gap in large_gaps:
                if gap and gap > 600:  # More than 10 minutes
                    gap_hours = gap / 3600
                    ts_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    prev_str = datetime.fromtimestamp(prev_ts).strftime('%Y-%m-%d %H:%M:%S') if prev_ts else "N/A"
                    logger.info(f"   Gap of {gap_hours:.1f} hours between {prev_str} and {ts_str}")
        
        conn.close()
        
        logger.info("\n" + "="*60)
        logger.info("✅ Database integrity check PASSED")
        logger.info("="*60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integrity check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_database_integrity()
    sys.exit(0 if success else 1)

