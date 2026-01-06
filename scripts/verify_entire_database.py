#!/usr/bin/env python3
"""
Comprehensive verification of the entire database
Samples candles from different time periods and verifies against Hyperliquid
"""

import sys
import os
from datetime import datetime
import time
import random

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


def verify_entire_database():
    """Comprehensive verification of entire database"""
    try:
        logger.info("=" * 80)
        logger.info("🔍 COMPREHENSIVE DATABASE VERIFICATION")
        logger.info("=" * 80)
        
        symbol = "BTC"
        storage = CandleStorage(symbol=symbol)
        hyperliquid_api = get_hyperliquid_api()
        
        # Get database stats
        candle_count = storage.get_candle_count()
        first_timestamp = storage.get_first_timestamp()
        last_timestamp = storage.get_last_timestamp()
        
        logger.info(f"\n📊 Database Overview:")
        logger.info(f"   Total candles: {candle_count:,}")
        logger.info(f"   First candle: {datetime.fromtimestamp(first_timestamp).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"   Last candle: {datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"   Time span: {((last_timestamp - first_timestamp) / (365.25 * 24 * 3600)):.2f} years")
        
        # Divide database into time periods for sampling
        time_span = last_timestamp - first_timestamp
        periods = [
            ("Beginning (First 10%)", first_timestamp, first_timestamp + (time_span * 0.1)),
            ("Early (10-30%)", first_timestamp + (time_span * 0.1), first_timestamp + (time_span * 0.3)),
            ("Mid-Early (30-50%)", first_timestamp + (time_span * 0.3), first_timestamp + (time_span * 0.5)),
            ("Mid-Late (50-70%)", first_timestamp + (time_span * 0.5), first_timestamp + (time_span * 0.7)),
            ("Recent (70-90%)", first_timestamp + (time_span * 0.7), first_timestamp + (time_span * 0.9)),
            ("Very Recent (Last 10%)", first_timestamp + (time_span * 0.9), last_timestamp),
        ]
        
        logger.info(f"\n📅 Sampling Strategy:")
        logger.info(f"   Will sample candles from {len(periods)} time periods")
        logger.info(f"   Each period: 20 random candles + verification with Hyperliquid (if available)")
        
        total_checked = 0
        total_matches = 0
        total_mismatches = 0
        total_hl_verified = 0
        total_hl_matches = 0
        
        for period_name, period_start, period_end in periods:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"📅 Period: {period_name}")
            logger.info(f"   Time range: {datetime.fromtimestamp(period_start).strftime('%Y-%m-%d %H:%M:%S')} to {datetime.fromtimestamp(period_end).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'=' * 80}")
            
            # Get all candles in this period
            period_candles = storage.get_candles_by_range(period_start, period_end)
            
            if not period_candles:
                logger.warning(f"   ⚠️ No candles found in this period")
                continue
            
            logger.info(f"   Found {len(period_candles)} candles in this period")
            
            # Sample 20 random candles (or all if less than 20)
            sample_size = min(20, len(period_candles))
            if len(period_candles) > sample_size:
                sampled_candles = random.sample(period_candles, sample_size)
            else:
                sampled_candles = period_candles
            
            logger.info(f"   Sampling {len(sampled_candles)} candles for verification...")
            
            # Verify data integrity for sampled candles
            period_matches = 0
            period_mismatches = 0
            period_hl_verified = 0
            period_hl_matches = 0
            
            for candle in sampled_candles:
                total_checked += 1
                
                # Basic data integrity check
                ts = candle.get('timestamp', 0)
                open_price = float(candle.get('open', 0))
                high_price = float(candle.get('high', 0))
                low_price = float(candle.get('low', 0))
                close_price = float(candle.get('close', 0))
                volume = float(candle.get('volume', 0))
                
                # Validate OHLCV data
                is_valid = True
                issues = []
                
                if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                    is_valid = False
                    issues.append("Invalid prices (zero or negative)")
                
                if high_price < low_price:
                    is_valid = False
                    issues.append(f"High < Low (H={high_price:.2f} L={low_price:.2f})")
                
                if high_price < open_price or high_price < close_price:
                    is_valid = False
                    issues.append(f"High < Open/Close")
                
                if low_price > open_price or low_price > close_price:
                    is_valid = False
                    issues.append(f"Low > Open/Close")
                
                if volume < 0:
                    is_valid = False
                    issues.append("Negative volume")
                
                if is_valid:
                    period_matches += 1
                    total_matches += 1
                else:
                    period_mismatches += 1
                    total_mismatches += 1
                    dt = datetime.fromtimestamp(ts)
                    logger.warning(f"   ❌ Invalid candle at {dt.strftime('%Y-%m-%d %H:%M:%S')}: {', '.join(issues)}")
                
                # Try to verify with Hyperliquid (only for recent data - last 7 days)
                # Hyperliquid API may not have very old data
                current_time = time.time()
                days_old = (current_time - ts) / (24 * 3600)
                
                if days_old <= 7:  # Only verify with Hyperliquid for last 7 days
                    try:
                        # Fetch candles around this timestamp
                        # Calculate how many candles to fetch (we need candles around this timestamp)
                        # Fetch 50 candles to ensure we get the one we need
                        hl_candles = hyperliquid_api.get_historical_candles(symbol, "5m", 50)
                        
                        if hl_candles:
                            # Find matching candle by timestamp
                            matching_hl = None
                            for hl_c in hl_candles:
                                if abs(hl_c.get('timestamp', 0) - ts) < 60:  # Within 1 minute tolerance
                                    matching_hl = hl_c
                                    break
                            
                            if matching_hl:
                                period_hl_verified += 1
                                total_hl_verified += 1
                                
                                # Compare prices
                                hl_open = float(matching_hl.get('open', 0))
                                hl_high = float(matching_hl.get('high', 0))
                                hl_low = float(matching_hl.get('low', 0))
                                hl_close = float(matching_hl.get('close', 0))
                                
                                tolerance = 0.01
                                prices_match = (
                                    abs(open_price - hl_open) <= tolerance and
                                    abs(high_price - hl_high) <= tolerance and
                                    abs(low_price - hl_low) <= tolerance and
                                    abs(close_price - hl_close) <= tolerance
                                )
                                
                                if prices_match:
                                    period_hl_matches += 1
                                    total_hl_matches += 1
                                else:
                                    dt = datetime.fromtimestamp(ts)
                                    logger.warning(f"   ⚠️ Price mismatch at {dt.strftime('%Y-%m-%d %H:%M:%S')}:")
                                    logger.warning(f"      DB: O={open_price:.2f} H={high_price:.2f} L={low_price:.2f} C={close_price:.2f}")
                                    logger.warning(f"      HL: O={hl_open:.2f} H={hl_high:.2f} L={hl_low:.2f} C={hl_close:.2f}")
                    except Exception as e:
                        logger.debug(f"   Could not verify with Hyperliquid: {e}")
            
            logger.info(f"   Period Results:")
            logger.info(f"      Data integrity: {period_matches}/{len(sampled_candles)} valid")
            logger.info(f"      Data issues: {period_mismatches}/{len(sampled_candles)} invalid")
            if period_hl_verified > 0:
                logger.info(f"      Hyperliquid verified: {period_hl_matches}/{period_hl_verified} match")
        
        # Final summary
        logger.info(f"\n{'=' * 80}")
        logger.info("📊 FINAL VERIFICATION SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"   Total candles checked: {total_checked}")
        logger.info(f"   Data integrity: {total_matches}/{total_checked} valid ({total_matches/total_checked*100:.1f}%)")
        logger.info(f"   Data issues: {total_mismatches}/{total_checked} invalid ({total_mismatches/total_checked*100:.1f}%)")
        logger.info(f"   Hyperliquid verified: {total_hl_verified} candles")
        logger.info(f"   Hyperliquid matches: {total_hl_matches}/{total_hl_verified} ({total_hl_matches/total_hl_verified*100:.1f}%)" if total_hl_verified > 0 else "   Hyperliquid verified: N/A (data too old)")
        
        if total_mismatches == 0 and (total_hl_verified == 0 or total_hl_matches == total_hl_verified):
            logger.info(f"\n   ✅ DATABASE VERIFICATION PASSED")
            logger.info(f"   All sampled candles have valid data structure")
            if total_hl_verified > 0:
                logger.info(f"   All verified candles match Hyperliquid perfectly")
        else:
            logger.warning(f"\n   ⚠️ DATABASE VERIFICATION FOUND ISSUES")
            if total_mismatches > 0:
                logger.warning(f"   {total_mismatches} candles have data integrity issues")
            if total_hl_verified > 0 and total_hl_matches < total_hl_verified:
                logger.warning(f"   {total_hl_verified - total_hl_matches} candles don't match Hyperliquid")
        
        logger.info(f"{'=' * 80}")
        
        # Additional check: Verify recent data (last 24 hours) matches perfectly
        logger.info(f"\n{'=' * 80}")
        logger.info("🔍 ADDITIONAL CHECK: Last 24 Hours")
        logger.info(f"{'=' * 80}")
        
        current_time = time.time()
        last_24h_start = current_time - (24 * 3600)
        current_5m_start = (int(current_time) // 300) * 300
        
        recent_db_candles = storage.get_candles_by_range(last_24h_start, current_5m_start)
        
        if recent_db_candles:
            logger.info(f"   Database has {len(recent_db_candles)} candles in last 24 hours")
            
            # Fetch from Hyperliquid
            hl_recent = hyperliquid_api.get_historical_candles(symbol, "5m", len(recent_db_candles) + 10)
            if hl_recent:
                # Filter completed candles
                hl_recent_completed = [c for c in hl_recent if c.get('timestamp', 0) < current_5m_start]
                hl_recent_completed = [c for c in hl_recent_completed if c.get('timestamp', 0) >= last_24h_start]
                hl_recent_completed.sort(key=lambda x: x.get('timestamp', 0))
                
                logger.info(f"   Hyperliquid has {len(hl_recent_completed)} completed candles in last 24 hours")
                
                # Compare
                hl_map = {c['timestamp']: c for c in hl_recent_completed}
                db_map = {c['timestamp']: c for c in recent_db_candles}
                common = sorted(set(hl_map.keys()) & set(db_map.keys()))
                
                recent_matches = 0
                recent_mismatches = 0
                
                for ts in common:
                    hl_c = hl_map[ts]
                    db_c = db_map[ts]
                    
                    all_match = True
                    for field in ['open', 'high', 'low', 'close']:
                        if abs(float(hl_c.get(field, 0)) - float(db_c.get(field, 0))) > 0.01:
                            all_match = False
                            break
                    
                    if all_match:
                        recent_matches += 1
                    else:
                        recent_mismatches += 1
                
                logger.info(f"   Recent data comparison:")
                logger.info(f"      Common candles: {len(common)}")
                logger.info(f"      Matches: {recent_matches}/{len(common)} ({recent_matches/len(common)*100:.1f}%)" if common else "      Matches: N/A")
                logger.info(f"      Mismatches: {recent_mismatches}/{len(common)} ({recent_mismatches/len(common)*100:.1f}%)" if common else "      Mismatches: N/A")
                
                if recent_mismatches == 0 and len(common) > 0:
                    logger.info(f"   ✅ Recent data (last 24h) matches Hyperliquid perfectly!")
                elif recent_mismatches > 0:
                    logger.warning(f"   ⚠️ Recent data has {recent_mismatches} mismatches")
        
        logger.info(f"{'=' * 80}")
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    verify_entire_database()

