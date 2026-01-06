#!/usr/bin/env python3
"""
Fix recent corrupted candles by replacing them with Hyperliquid data
Only fixes the last 24 hours to preserve older Binance data
"""

import sys
import os
from datetime import datetime
import time

# Setup Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger
from core.services.candle_storage import CandleStorage
from core.api.hyperliquid_api import get_hyperliquid_api

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def fix_recent_candles():
    """Replace last 24 hours of candles with Hyperliquid data"""
    try:
        logger.info("=" * 80)
        logger.info("🔧 FIXING RECENT CANDLES (Last 24 Hours)")
        logger.info("=" * 80)
        
        symbol = "BTC"
        hours = 24
        candle_count = hours * 12  # 12 candles per hour
        
        storage = CandleStorage(symbol=symbol)
        hyperliquid_api = get_hyperliquid_api()
        
        # Get current time and calculate cutoff
        current_time = time.time()
        cutoff_time = current_time - (hours * 3600)  # 24 hours ago
        
        logger.info(f"\n📊 Step 1: Fetching last {hours} hours ({candle_count} candles) from Hyperliquid...")
        
        # Fetch from Hyperliquid
        hl_candles_raw = hyperliquid_api.get_historical_candles(symbol, "5m", candle_count + 10)
        
        if not hl_candles_raw:
            logger.error("❌ Failed to fetch candles from Hyperliquid")
            return
        
        # Filter to only completed candles
        current_5m_start = (int(current_time) // 300) * 300
        hl_candles = [c for c in hl_candles_raw if c.get('timestamp', 0) < current_5m_start]
        hl_candles = [c for c in hl_candles if c.get('timestamp', 0) >= cutoff_time]
        hl_candles.sort(key=lambda x: x.get('timestamp', 0))
        
        if not hl_candles:
            logger.error("❌ No completed candles found from Hyperliquid")
            return
        
        logger.info(f"   ✅ Fetched {len(hl_candles)} completed candles from Hyperliquid")
        logger.info(f"   First candle: {datetime.fromtimestamp(hl_candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"   Last candle: {datetime.fromtimestamp(hl_candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Get timestamps to replace
        timestamps_to_replace = {c['timestamp'] for c in hl_candles}
        
        logger.info(f"\n🗑️ Step 2: Deleting corrupted candles from database...")
        
        # Delete candles in this time range
        import sqlite3
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM candles_5m
            WHERE timestamp >= ? AND timestamp < ?
        """, (cutoff_time, current_5m_start))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"   ✅ Deleted {deleted_count} candles from database")
        
        logger.info(f"\n💾 Step 3: Inserting correct Hyperliquid candles...")
        
        # Insert correct candles
        storage.insert_candles(hl_candles)
        
        logger.info(f"   ✅ Inserted {len(hl_candles)} correct candles from Hyperliquid")
        
        # Verify
        logger.info(f"\n✅ Step 4: Verifying fix...")
        
        db_candles = storage.get_candles_by_range(cutoff_time, current_5m_start)
        
        if not db_candles:
            logger.error("❌ No candles found in database after fix")
            return
        
        logger.info(f"   Database now has {len(db_candles)} candles in the fixed range")
        
        # Compare
        hl_map = {c['timestamp']: c for c in hl_candles}
        db_map = {c['timestamp']: c for c in db_candles}
        common = set(hl_map.keys()) & set(db_map.keys())
        
        matches = 0
        mismatches = 0
        
        for ts in sorted(common):
            hl_c = hl_map[ts]
            db_c = db_map[ts]
            
            all_match = True
            for field in ['open', 'high', 'low', 'close']:
                if abs(float(hl_c.get(field, 0)) - float(db_c.get(field, 0))) > 0.01:
                    all_match = False
                    break
            
            if all_match:
                matches += 1
            else:
                mismatches += 1
        
        logger.info(f"   Matches: {matches}/{len(common)}")
        logger.info(f"   Mismatches: {mismatches}/{len(common)}")
        
        if mismatches == 0:
            logger.info(f"\n   ✅ PERFECT! All recent candles now match Hyperliquid")
        else:
            logger.warning(f"\n   ⚠️ Still have {mismatches} mismatches - may need to investigate further")
        
        logger.info("=" * 80)
        logger.info("✅ FIX COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Fix failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    fix_recent_candles()

