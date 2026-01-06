#!/usr/bin/env python3
"""
Compare candle data from Hyperliquid, Binance, and Database
Fetches last 20 candles from each source and compares them
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.services.candle_storage import CandleStorage
from core.api.hyperliquid_api import get_hyperliquid_api
from core.external.binance_api import BinanceAPI
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)


def format_candle(candle):
    """Format candle for display"""
    if isinstance(candle, dict):
        timestamp = candle.get('timestamp', 0)
        dt = datetime.fromtimestamp(timestamp)
        return {
            'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'open': candle.get('open', 0),
            'high': candle.get('high', 0),
            'low': candle.get('low', 0),
            'close': candle.get('close', 0),
            'volume': candle.get('volume', 0)
        }
    return candle


def compare_candles(candle1, candle2, source1_name, source2_name, tolerance=0.01):
    """Compare two candles and return differences"""
    differences = []
    
    # Compare prices
    for field in ['open', 'high', 'low', 'close']:
        val1 = candle1.get(field, 0)
        val2 = candle2.get(field, 0)
        diff = abs(val1 - val2)
        diff_pct = (diff / val1 * 100) if val1 > 0 else 0
        
        if diff > tolerance:
            differences.append({
                'field': field,
                f'{source1_name}': val1,
                f'{source2_name}': val2,
                'diff': diff,
                'diff_pct': diff_pct
            })
    
    # Compare timestamps (should be within 5 minutes)
    ts1 = candle1.get('timestamp', 0)
    ts2 = candle2.get('timestamp', 0)
    ts_diff = abs(ts1 - ts2)
    if ts_diff > 300:  # 5 minutes
        differences.append({
            'field': 'timestamp',
            f'{source1_name}': datetime.fromtimestamp(ts1).strftime('%Y-%m-%d %H:%M:%S'),
            f'{source2_name}': datetime.fromtimestamp(ts2).strftime('%Y-%m-%d %H:%M:%S'),
            'diff': f'{ts_diff/60:.1f} minutes'
        })
    
    return differences


def main():
    """Compare candle data from all sources"""
    try:
        logger.info("=" * 80)
        logger.info("🔍 COMPARING CANDLE DATA FROM HYPERLIQUID, BINANCE, AND DATABASE")
        logger.info("=" * 80)
        
        # Update database first
        logger.info("\n📥 Step 1: Updating database with latest candles...")
        storage = CandleStorage(symbol="BTC")
        storage.backfill_missing_candles()
        logger.info("✅ Database updated")
        
        # Get candles from database
        logger.info("\n📊 Step 2: Fetching last 20 candles from DATABASE...")
        db_candles = storage.get_candles_by_count(20)
        if not db_candles:
            logger.error("❌ No candles in database!")
            return
        
        logger.info(f"✅ Found {len(db_candles)} candles in database")
        logger.info(f"   First candle: {datetime.fromtimestamp(db_candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Last candle: {datetime.fromtimestamp(db_candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get candles from Hyperliquid
        logger.info("\n📊 Step 3: Fetching last 20 candles from HYPERLIQUID...")
        hyperliquid_api = get_hyperliquid_api()
        hyperliquid_candles = hyperliquid_api.get_historical_candles("BTC", "5m", 20)
        if not hyperliquid_candles:
            logger.error("❌ Failed to fetch candles from Hyperliquid!")
            return
        
        logger.info(f"✅ Found {len(hyperliquid_candles)} candles from Hyperliquid")
        logger.info(f"   First candle: {datetime.fromtimestamp(hyperliquid_candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Last candle: {datetime.fromtimestamp(hyperliquid_candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get candles from Binance
        logger.info("\n📊 Step 4: Fetching last 20 candles from BINANCE...")
        binance_api = BinanceAPI()
        
        # Calculate time range for last 20 candles (20 * 5 minutes = 100 minutes)
        import time
        end_time_ms = int(time.time() * 1000)
        start_time_ms = end_time_ms - (20 * 5 * 60 * 1000)  # 100 minutes ago
        
        binance_candles_raw = binance_api.get_historical_klines("BTCUSDT", "5m", start_time=start_time_ms, end_time=end_time_ms, limit=20)
        if not binance_candles_raw:
            logger.error("❌ Failed to fetch candles from Binance!")
            return
        
        # Binance API already returns list of dictionaries with our format
        # Just take the last 20
        binance_candles = binance_candles_raw[-20:] if len(binance_candles_raw) > 20 else binance_candles_raw
        
        # Ensure timestamps are integers (not floats)
        for candle in binance_candles:
            if 'timestamp' in candle:
                candle['timestamp'] = int(candle['timestamp'])
        
        logger.info(f"✅ Found {len(binance_candles)} candles from Binance")
        logger.info(f"   First candle: {datetime.fromtimestamp(binance_candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Last candle: {datetime.fromtimestamp(binance_candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Compare Database vs Hyperliquid
        logger.info("\n" + "=" * 80)
        logger.info("🔍 COMPARISON: DATABASE vs HYPERLIQUID")
        logger.info("=" * 80)
        
        db_hl_matches = 0
        db_hl_mismatches = 0
        
        for i, (db_candle, hl_candle) in enumerate(zip(db_candles, hyperliquid_candles)):
            differences = compare_candles(db_candle, hl_candle, "DATABASE", "HYPERLIQUID")
            if differences:
                db_hl_mismatches += 1
                logger.warning(f"\n⚠️  Candle {i+1} MISMATCH:")
                logger.warning(f"   DB Timestamp: {datetime.fromtimestamp(db_candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                logger.warning(f"   HL Timestamp: {datetime.fromtimestamp(hl_candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                for diff in differences:
                    logger.warning(f"   {diff['field']}: DB={diff.get('DATABASE', 'N/A')} | HL={diff.get('HYPERLIQUID', 'N/A')} | Diff={diff.get('diff', 'N/A')} ({diff.get('diff_pct', 0):.3f}%)")
            else:
                db_hl_matches += 1
        
        logger.info(f"\n📊 Summary: {db_hl_matches}/{len(db_candles)} matches, {db_hl_mismatches} mismatches")
        
        # Compare Database vs Binance
        logger.info("\n" + "=" * 80)
        logger.info("🔍 COMPARISON: DATABASE vs BINANCE")
        logger.info("=" * 80)
        
        db_bn_matches = 0
        db_bn_mismatches = 0
        
        for i, (db_candle, bn_candle) in enumerate(zip(db_candles, binance_candles)):
            differences = compare_candles(db_candle, bn_candle, "DATABASE", "BINANCE")
            if differences:
                db_bn_mismatches += 1
                logger.warning(f"\n⚠️  Candle {i+1} MISMATCH:")
                logger.warning(f"   DB Timestamp: {datetime.fromtimestamp(db_candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                logger.warning(f"   BN Timestamp: {datetime.fromtimestamp(bn_candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                for diff in differences:
                    logger.warning(f"   {diff['field']}: DB={diff.get('DATABASE', 'N/A')} | BN={diff.get('BINANCE', 'N/A')} | Diff={diff.get('diff', 'N/A')} ({diff.get('diff_pct', 0):.3f}%)")
            else:
                db_bn_matches += 1
        
        logger.info(f"\n📊 Summary: {db_bn_matches}/{len(db_candles)} matches, {db_bn_mismatches} mismatches")
        
        # Compare Hyperliquid vs Binance
        logger.info("\n" + "=" * 80)
        logger.info("🔍 COMPARISON: HYPERLIQUID vs BINANCE")
        logger.info("=" * 80)
        
        hl_bn_matches = 0
        hl_bn_mismatches = 0
        
        for i, (hl_candle, bn_candle) in enumerate(zip(hyperliquid_candles, binance_candles)):
            differences = compare_candles(hl_candle, bn_candle, "HYPERLIQUID", "BINANCE")
            if differences:
                hl_bn_mismatches += 1
                logger.warning(f"\n⚠️  Candle {i+1} MISMATCH:")
                logger.warning(f"   HL Timestamp: {datetime.fromtimestamp(hl_candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                logger.warning(f"   BN Timestamp: {datetime.fromtimestamp(bn_candle['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                for diff in differences:
                    logger.warning(f"   {diff['field']}: HL={diff.get('HYPERLIQUID', 'N/A')} | BN={diff.get('BINANCE', 'N/A')} | Diff={diff.get('diff', 'N/A')} ({diff.get('diff_pct', 0):.3f}%)")
            else:
                hl_bn_matches += 1
        
        logger.info(f"\n📊 Summary: {hl_bn_matches}/{len(hyperliquid_candles)} matches, {hl_bn_mismatches} mismatches")
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Database vs Hyperliquid: {db_hl_matches}/{len(db_candles)} matches")
        logger.info(f"Database vs Binance: {db_bn_matches}/{len(db_candles)} matches")
        logger.info(f"Hyperliquid vs Binance: {hl_bn_matches}/{len(hyperliquid_candles)} matches")
        
        if db_hl_mismatches == 0:
            logger.info("\n✅ Database matches Hyperliquid perfectly!")
        else:
            logger.warning(f"\n⚠️  Database has {db_hl_mismatches} mismatches with Hyperliquid")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Comparison interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Comparison failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

