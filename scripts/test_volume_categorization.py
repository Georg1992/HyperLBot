#!/usr/bin/env python3
"""
Test Volume Categorization
Tests percentile-based volume categorization and shows actual BTC thresholds
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.calculations.volume_data_provider import VolumeDataProvider
from core.calculations.volume_classifier import VolumeClassifier
from loguru import logger

def test_volume_categorization():
    """Test volume categorization and show percentile thresholds"""
    try:
        logger.info("🧪 Testing volume categorization...")
        
        # Initialize components
        data_provider = VolumeDataProvider("BTC")
        classifier = VolumeClassifier()
        
        # 1. Fetch volume history from database
        logger.info("📊 Fetching volume history from database...")
        try:
            volume_history = data_provider.get_volume_history(10)
            logger.info(f"✅ Fetched {len(volume_history)} volume records")
        except ValueError as e:
            logger.error(f"❌ Failed to fetch volume history: {e}")
            return
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return
        
        if not volume_history or len(volume_history) < 20:
            logger.error(f"❌ Insufficient volume history: {len(volume_history)} records")
            return
        
        # 2. Extract volumes and calculate percentiles manually
        volumes = [v.get('volume', 0.0) for v in volume_history if v.get('volume', 0.0) > 0]
        sorted_volumes = sorted(volumes)
        n = len(sorted_volumes)
        
        percentile_10 = sorted_volumes[int(n * 0.10)]
        percentile_25 = sorted_volumes[int(n * 0.25)]
        percentile_50 = sorted_volumes[int(n * 0.50)]
        percentile_75 = sorted_volumes[int(n * 0.75)]
        percentile_90 = sorted_volumes[int(n * 0.90)]
        percentile_95 = sorted_volumes[int(n * 0.95)]
        
        # 3. Display percentile thresholds
        logger.info("\n" + "="*60)
        logger.info("📊 VOLUME CATEGORIZATION THRESHOLDS (Percentile-Based)")
        logger.info("="*60)
        logger.info(f"Sample Size: {n} completed 5-minute candles (last 7 days)")
        logger.info("")
        logger.info("Category Thresholds (in BTC for 5-minute period):")
        logger.info(f"  VERY_LOW:  < {percentile_10:.2f} BTC  (< 10th percentile)")
        logger.info(f"  LOW:       {percentile_10:.2f} - {percentile_25:.2f} BTC  (10th-25th percentile)")
        logger.info(f"  NORMAL:    {percentile_25:.2f} - {percentile_75:.2f} BTC  (25th-75th percentile)")
        logger.info(f"  HIGH:      {percentile_75:.2f} - {percentile_90:.2f} BTC  (75th-90th percentile)")
        logger.info(f"  VERY_HIGH: {percentile_90:.2f} - {percentile_95:.2f} BTC  (90th-95th percentile)")
        logger.info(f"  EXTREME:   ≥ {percentile_95:.2f} BTC  (≥95th percentile)")
        logger.info("")
        logger.info("Percentile Values:")
        logger.info(f"  10th percentile (P10): {percentile_10:.2f} BTC")
        logger.info(f"  25th percentile (P25/Q1): {percentile_25:.2f} BTC")
        logger.info(f"  50th percentile (P50/Median): {percentile_50:.2f} BTC")
        logger.info(f"  75th percentile (P75/Q3): {percentile_75:.2f} BTC")
        logger.info(f"  90th percentile (P90): {percentile_90:.2f} BTC")
        logger.info(f"  95th percentile (P95): {percentile_95:.2f} BTC")
        logger.info("")
        
        # 4. Test categorization with example volumes
        logger.info("="*60)
        logger.info("🧪 TESTING CATEGORIZATION WITH EXAMPLE VOLUMES")
        logger.info("="*60)
        
        test_volumes = [
            0.1,      # Very small
            1.0,      # Small
            10.0,     # Medium-small
            50.0,     # Medium
            100.0,    # Medium-large
            500.0,    # Large
            1000.0,   # Very large (user's example)
            2000.0,   # Extreme
        ]
        
        for test_volume in test_volumes:
            try:
                result = classifier.categorize_volume(test_volume, 1.0, volume_history)
                level = result.get("level", "UNKNOWN")
                description = result.get("description", "")
                
                logger.info(f"  {test_volume:>7.1f} BTC → {level:>10} ({description})")
            except Exception as e:
                logger.error(f"  {test_volume:>7.1f} BTC → ERROR: {e}")
        
        logger.info("")
        
        # 5. Show current market price for USD conversion
        try:
            from core.api.hyperliquid_api import get_hyperliquid_api
            api = get_hyperliquid_api()
            current_price = api.get_current_price("BTC")
            
            if current_price:
                logger.info("="*60)
                logger.info("💰 USD EQUIVALENTS (at current BTC price)")
                logger.info("="*60)
                logger.info(f"Current BTC Price: ${current_price:,.2f}")
                logger.info("")
                logger.info("Category Thresholds (in USD for 5-minute period):")
                logger.info(f"  VERY_LOW:  < ${percentile_10 * current_price:,.2f}  (< 10th percentile)")
                logger.info(f"  LOW:       ${percentile_10 * current_price:,.2f} - ${percentile_25 * current_price:,.2f}  (10th-25th percentile)")
                logger.info(f"  NORMAL:    ${percentile_25 * current_price:,.2f} - ${percentile_75 * current_price:,.2f}  (25th-75th percentile)")
                logger.info(f"  HIGH:      ${percentile_75 * current_price:,.2f} - ${percentile_90 * current_price:,.2f}  (75th-90th percentile)")
                logger.info(f"  VERY_HIGH: ${percentile_90 * current_price:,.2f} - ${percentile_95 * current_price:,.2f}  (90th-95th percentile)")
                logger.info(f"  EXTREME:   ≥ ${percentile_95 * current_price:,.2f}  (≥95th percentile)")
                logger.info("")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch current price for USD conversion: {e}")
        
        logger.info("="*60)
        logger.info("✅ Volume categorization test complete!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    test_volume_categorization()

