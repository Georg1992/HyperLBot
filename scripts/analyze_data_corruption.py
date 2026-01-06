#!/usr/bin/env python3
"""
Analyze data corruption - check if mismatches are in recent or old data
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


def analyze_corruption():
    """Analyze if data is corrupted or just old Binance data"""
    try:
        logger.info("=" * 80)
        logger.info("🔍 ANALYZING DATA CORRUPTION")
        logger.info("=" * 80)
        
        symbol = "BTC"
        storage = CandleStorage(symbol=symbol)
        hyperliquid_api = get_hyperliquid_api()
        
        current_time = time.time()
        
        # Test different time periods
        test_periods = [
            ("Last 1 hour", 1),
            ("Last 3 hours", 3),
            ("Last 6 hours", 6),
            ("Last 12 hours", 12),
            ("Last 24 hours", 24),
        ]
        
        logger.info(f"\n📊 Testing different time periods to identify corruption pattern...")
        
        for period_name, hours in test_periods:
            candle_count = hours * 12  # 12 candles per hour
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"📅 Testing: {period_name} ({candle_count} candles)")
            logger.info(f"{'=' * 80}")
            
            # Fetch from Hyperliquid
            hl_candles_raw = hyperliquid_api.get_historical_candles(symbol, "5m", candle_count + 5)
            
            if not hl_candles_raw:
                logger.error(f"❌ Failed to fetch from Hyperliquid")
                continue
            
            # Filter completed candles
            current_5m_start = (int(current_time) // 300) * 300
            hl_candles = [c for c in hl_candles_raw if c['timestamp'] < current_5m_start]
            hl_candles = hl_candles[-candle_count:] if len(hl_candles) >= candle_count else hl_candles
            
            if not hl_candles:
                logger.warning(f"⚠️ No completed candles from Hyperliquid")
                continue
            
            # Fetch from database
            hl_first_ts = hl_candles[0]['timestamp']
            hl_last_ts = hl_candles[-1]['timestamp']
            db_candles = storage.get_candles_by_range(hl_first_ts, hl_last_ts)
            
            if not db_candles:
                logger.warning(f"⚠️ No candles in database for this period")
                continue
            
            # Compare
            hl_map = {c['timestamp']: c for c in hl_candles}
            db_map = {c['timestamp']: c for c in db_candles}
            common_timestamps = sorted(set(hl_map.keys()) & set(db_map.keys()))
            
            if not common_timestamps:
                logger.warning(f"⚠️ No common timestamps")
                continue
            
            # Count matches and mismatches
            matches = 0
            mismatches = 0
            tolerance = 0.01
            
            mismatch_details = []
            
            for ts in common_timestamps:
                hl_c = hl_map[ts]
                db_c = db_map[ts]
                
                price_mismatch = False
                max_price_diff = 0
                
                for field in ['open', 'high', 'low', 'close']:
                    hl_val = float(hl_c.get(field, 0))
                    db_val = float(db_c.get(field, 0))
                    diff = abs(hl_val - db_val)
                    max_price_diff = max(max_price_diff, diff)
                    
                    if diff > tolerance:
                        price_mismatch = True
                
                if price_mismatch:
                    mismatches += 1
                    mismatch_details.append({
                        'timestamp': ts,
                        'max_diff': max_price_diff
                    })
                else:
                    matches += 1
            
            match_rate = (matches / len(common_timestamps) * 100) if common_timestamps else 0
            
            logger.info(f"   Common candles: {len(common_timestamps)}")
            logger.info(f"   Matches: {matches} ({match_rate:.1f}%)")
            logger.info(f"   Mismatches: {mismatches} ({100 - match_rate:.1f}%)")
            
            if mismatches > 0:
                # Show worst mismatches
                mismatch_details.sort(key=lambda x: x['max_diff'], reverse=True)
                logger.warning(f"   Worst mismatches:")
                for detail in mismatch_details[:5]:
                    dt = datetime.fromtimestamp(detail['timestamp'])
                    logger.warning(f"      {dt.strftime('%Y-%m-%d %H:%M:%S')}: ${detail['max_diff']:.2f} difference")
        
        # Check if recent data (last 1 hour) matches perfectly
        logger.info(f"\n{'=' * 80}")
        logger.info("🔍 DETAILED ANALYSIS: Last 1 Hour (Most Recent)")
        logger.info(f"{'=' * 80}")
        
        # Fetch last 12 candles (1 hour)
        hl_recent = hyperliquid_api.get_historical_candles(symbol, "5m", 15)
        if hl_recent:
            current_5m_start = (int(current_time) // 300) * 300
            hl_recent = [c for c in hl_recent if c['timestamp'] < current_5m_start][-12:]
            
            if hl_recent:
                logger.info(f"   Hyperliquid last 12 candles:")
                for c in hl_recent:
                    dt = datetime.fromtimestamp(c['timestamp'])
                    logger.info(f"      {dt.strftime('%Y-%m-%d %H:%M:%S')}: O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f} V={c['volume']:.2f}")
                
                # Get from database
                hl_first_ts = hl_recent[0]['timestamp']
                hl_last_ts = hl_recent[-1]['timestamp']
                db_recent = storage.get_candles_by_range(hl_first_ts, hl_last_ts)
                
                if db_recent:
                    logger.info(f"\n   Database last 12 candles:")
                    for c in db_recent:
                        dt = datetime.fromtimestamp(c['timestamp'])
                        logger.info(f"      {dt.strftime('%Y-%m-%d %H:%M:%S')}: O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f} V={c['volume']:.2f}")
                    
                    # Compare
                    logger.info(f"\n   Comparison:")
                    hl_map = {c['timestamp']: c for c in hl_recent}
                    db_map = {c['timestamp']: c for c in db_recent}
                    
                    perfect_matches = 0
                    for ts in sorted(set(hl_map.keys()) & set(db_map.keys())):
                        hl_c = hl_map[ts]
                        db_c = db_map[ts]
                        
                        all_match = True
                        for field in ['open', 'high', 'low', 'close']:
                            if abs(float(hl_c.get(field, 0)) - float(db_c.get(field, 0))) > 0.01:
                                all_match = False
                                dt = datetime.fromtimestamp(ts)
                                logger.warning(f"      ❌ {dt.strftime('%Y-%m-%d %H:%M:%S')}: {field} mismatch (HL={hl_c.get(field, 0):.2f} DB={db_c.get(field, 0):.2f})")
                                break
                        
                        if all_match:
                            perfect_matches += 1
                    
                    if perfect_matches == len(set(hl_map.keys()) & set(db_map.keys())):
                        logger.info(f"   ✅ All recent candles match perfectly!")
                    else:
                        logger.warning(f"   ⚠️ Only {perfect_matches}/{len(set(hl_map.keys()) & set(db_map.keys()))} recent candles match")
        
        # Conclusion
        logger.info(f"\n{'=' * 80}")
        logger.info("📋 CONCLUSION")
        logger.info(f"{'=' * 80}")
        logger.info("   If recent data (last 1-3 hours) matches Hyperliquid:")
        logger.info("   ✅ Database is updating correctly with Hyperliquid data")
        logger.info("   ⚠️ Older mismatches are from initial Binance fetch (expected)")
        logger.info("")
        logger.info("   If recent data also has mismatches:")
        logger.info("   ❌ Database update mechanism may be broken")
        logger.info("   ❌ Need to investigate why new candles don't match")
        logger.info(f"{'=' * 80}")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    analyze_corruption()

