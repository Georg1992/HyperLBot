#!/usr/bin/env python3
"""
Update database and compare 12 hours of 5m candles from Hyperliquid with database
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


def compare_12h_candles():
    """Update database and compare 12 hours of candles"""
    try:
        logger.info("=" * 80)
        logger.info("🔄 UPDATING DATABASE AND COMPARING 12H OF CANDLES")
        logger.info("=" * 80)
        
        symbol = "BTC"
        hours = 12
        candle_count = hours * 12  # 12 candles per hour (5-minute intervals)
        
        # Step 1: Update database
        logger.info(f"\n📥 Step 1: Updating database with latest candles...")
        storage = CandleStorage(symbol=symbol)
        
        # Show current status
        current_count = storage.get_candle_count()
        current_last = storage.get_last_timestamp()
        if current_last:
            logger.info(f"   Current database: {current_count:,} candles")
            logger.info(f"   Last candle: {datetime.fromtimestamp(current_last).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Backfill missing candles
        storage.backfill_missing_candles()
        
        # Show updated status
        updated_count = storage.get_candle_count()
        updated_last = storage.get_last_timestamp()
        if updated_last:
            logger.info(f"   Updated database: {updated_count:,} candles")
            logger.info(f"   Last candle: {datetime.fromtimestamp(updated_last).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            if updated_count > current_count:
                logger.info(f"   ✅ Added {updated_count - current_count} new candles")
            else:
                logger.info(f"   💡 Database was already up to date")
        
        # Step 2: Fetch 12 hours of candles from Hyperliquid
        logger.info(f"\n📊 Step 2: Fetching last {hours} hours ({candle_count} candles) from Hyperliquid...")
        hyperliquid_api = get_hyperliquid_api()
        
        # Calculate time range for 12 hours
        current_time = time.time()
        start_time = current_time - (hours * 3600)  # 12 hours ago
        
        # Fetch candles from Hyperliquid
        # We'll fetch slightly more to ensure we get completed candles
        hl_candles_raw = hyperliquid_api.get_historical_candles(symbol, "5m", candle_count + 5)
        
        if not hl_candles_raw:
            logger.error("❌ Failed to fetch candles from Hyperliquid")
            return
        
        # Filter to get only completed candles (exclude ongoing)
        current_5m_start = (int(current_time) // 300) * 300
        hl_candles = []
        for candle in hl_candles_raw:
            if candle['timestamp'] < current_5m_start:
                hl_candles.append(candle)
        
        # Take the last candle_count candles
        hl_candles = hl_candles[-candle_count:] if len(hl_candles) >= candle_count else hl_candles
        
        if not hl_candles:
            logger.error("❌ No completed candles found from Hyperliquid")
            return
        
        logger.info(f"   ✅ Fetched {len(hl_candles)} completed candles from Hyperliquid")
        logger.info(f"   First candle: {datetime.fromtimestamp(hl_candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"   Last candle: {datetime.fromtimestamp(hl_candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Step 3: Fetch same candles from database
        logger.info(f"\n📊 Step 3: Fetching same candles from database...")
        
        # Get the timestamp range
        hl_first_ts = hl_candles[0]['timestamp']
        hl_last_ts = hl_candles[-1]['timestamp']
        
        # Fetch from database using get_candles_by_range
        db_candles = storage.get_candles_by_range(hl_first_ts, hl_last_ts)
        
        if not db_candles:
            logger.error("❌ No candles found in database for the time range")
            return
        
        logger.info(f"   ✅ Found {len(db_candles)} candles in database for the time range")
        logger.info(f"   First candle: {datetime.fromtimestamp(db_candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"   Last candle: {datetime.fromtimestamp(db_candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Step 4: Compare candles
        logger.info(f"\n🔍 Step 4: Comparing candles...")
        logger.info("=" * 80)
        
        # Create a map of timestamps to candles for easier comparison
        hl_map = {c['timestamp']: c for c in hl_candles}
        db_map = {c['timestamp']: c for c in db_candles}
        
        # Find common timestamps
        common_timestamps = set(hl_map.keys()) & set(db_map.keys())
        hl_only = set(hl_map.keys()) - set(db_map.keys())
        db_only = set(db_map.keys()) - set(hl_map.keys())
        
        logger.info(f"   Hyperliquid candles: {len(hl_candles)}")
        logger.info(f"   Database candles: {len(db_candles)}")
        logger.info(f"   Common timestamps: {len(common_timestamps)}")
        logger.info(f"   Hyperliquid only: {len(hl_only)}")
        logger.info(f"   Database only: {len(db_only)}")
        
        if hl_only:
            logger.warning(f"\n   ⚠️ Candles in Hyperliquid but not in database:")
            for ts in sorted(hl_only)[:10]:  # Show first 10
                logger.warning(f"      {datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            if len(hl_only) > 10:
                logger.warning(f"      ... and {len(hl_only) - 10} more")
        
        if db_only:
            logger.warning(f"\n   ⚠️ Candles in database but not in Hyperliquid:")
            for ts in sorted(db_only)[:10]:  # Show first 10
                logger.warning(f"      {datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            if len(db_only) > 10:
                logger.warning(f"      ... and {len(db_only) - 10} more")
        
        # Compare common candles
        matches = 0
        mismatches = 0
        tolerance = 0.01  # $0.01 tolerance for price differences
        
        logger.info(f"\n   Comparing {len(common_timestamps)} common candles...")
        
        for ts in sorted(common_timestamps):
            hl_c = hl_map[ts]
            db_c = db_map[ts]
            
            # Compare OHLCV
            price_mismatch = False
            mismatch_details = []
            
            for field in ['open', 'high', 'low', 'close']:
                hl_val = float(hl_c.get(field, 0))
                db_val = float(db_c.get(field, 0))
                diff = abs(hl_val - db_val)
                
                if diff > tolerance:
                    price_mismatch = True
                    mismatch_details.append(f"{field}: HL={hl_val:.2f} DB={db_val:.2f} (diff={diff:.2f})")
            
            # Compare volume (more lenient tolerance)
            volume_tolerance = 0.1
            hl_vol = float(hl_c.get('volume', 0))
            db_vol = float(db_c.get('volume', 0))
            vol_diff = abs(hl_vol - db_vol)
            
            if vol_diff > volume_tolerance and max(hl_vol, db_vol) > 0:
                price_mismatch = True
                mismatch_details.append(f"volume: HL={hl_vol:.2f} DB={db_vol:.2f} (diff={vol_diff:.2f})")
            
            if price_mismatch:
                mismatches += 1
                if mismatches <= 10:  # Show first 10 mismatches
                    logger.warning(f"\n   ⚠️ Mismatch at {datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')} UTC:")
                    for detail in mismatch_details:
                        logger.warning(f"      {detail}")
            else:
                matches += 1
        
        # Summary
        logger.info(f"\n" + "=" * 80)
        logger.info("📊 COMPARISON SUMMARY")
        logger.info("=" * 80)
        logger.info(f"   Total candles compared: {len(common_timestamps)}")
        logger.info(f"   Matches: {matches}")
        logger.info(f"   Mismatches: {mismatches}")
        logger.info(f"   Match rate: {(matches / len(common_timestamps) * 100):.1f}%" if common_timestamps else "N/A")
        
        if matches == len(common_timestamps) and not hl_only and not db_only:
            logger.info(f"\n   ✅ PERFECT MATCH! All candles match between Hyperliquid and database")
        elif matches > len(common_timestamps) * 0.95:  # 95% match rate
            logger.info(f"\n   ✅ Good match! Most candles match ({(matches / len(common_timestamps) * 100):.1f}%)")
        else:
            logger.warning(f"\n   ⚠️ Significant mismatches found ({(matches / len(common_timestamps) * 100):.1f}% match rate)")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    compare_12h_candles()

