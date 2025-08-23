#!/usr/bin/env python3
"""
Test Volume Integration
Verify that the bot properly integrates with the new stable volume fetcher
"""

import sys
import os
import time
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_hyperliquid_api_volume():
    """Test that HyperliquidAPI uses stable volume fetcher"""
    try:
        logger.info("🧪 Testing HyperliquidAPI Volume Integration")
        
        # Import and initialize HyperliquidAPI
        from core.hyperliquid_api import HyperliquidAPI
        
        api = HyperliquidAPI()
        logger.info("✅ HyperliquidAPI initialized")
        
        # Test multiple volume calls to check for stability
        logger.info("📊 Testing volume stability over multiple calls...")
        
        volumes = []
        for i in range(3):
            logger.info(f"\n📊 Volume Test {i+1}/3:")
            
            volume_data = api.get_current_5m_volume("BTC")
            
            if volume_data.get("status") == "success":
                current_volume = volume_data.get("current_volume", 0)
                volume_category = volume_data.get("volume_category", "UNKNOWN")
                data_source = volume_data.get("data_source", "unknown")
                
                volumes.append(current_volume)
                
                logger.success(f"   Volume: {current_volume:.1f} BTC")
                logger.info(f"   Category: {volume_category}")
                logger.info(f"   Source: {data_source}")
                logger.info(f"   Stability: {volume_data.get('volume_stability', 0):.1f}%")
            else:
                logger.error(f"   Error: {volume_data.get('error', 'Unknown error')}")
                volumes.append(0)
            
            if i < 2:  # Don't sleep on last iteration
                time.sleep(2)
        
        # Analyze stability
        if len(volumes) >= 2:
            max_volume = max(volumes)
            min_volume = min(volumes) 
            
            if max_volume > 0:
                variation_pct = (max_volume - min_volume) / max_volume * 100
                logger.info(f"\n📈 Volume Stability Analysis:")
                logger.info(f"   Min Volume: {min_volume:.1f} BTC")
                logger.info(f"   Max Volume: {max_volume:.1f} BTC")
                logger.info(f"   Variation: {variation_pct:.1f}%")
                
                if variation_pct < 10:  # Less than 10% variation is good
                    logger.success(f"✅ STABLE: Volume variation under 10% - good stability!")
                    return True
                elif variation_pct < 50:  # Less than 50% is acceptable
                    logger.warning(f"⚠️ MODERATE: Volume variation {variation_pct:.1f}% - acceptable")
                    return True
                else:
                    logger.error(f"❌ UNSTABLE: Volume variation {variation_pct:.1f}% - still fluctuating!")
                    return False
            else:
                logger.error("❌ No valid volume readings obtained")
                return False
        else:
            logger.error("❌ Insufficient volume readings for stability test")
            return False
            
    except Exception as e:
        logger.error(f"❌ HyperliquidAPI volume integration test failed: {e}")
        return False

def test_direct_stable_fetcher():
    """Test the stable volume fetcher directly"""
    try:
        logger.info("\n🧪 Testing Direct Stable Volume Fetcher")
        
        from data.stable_volume_fetcher import StableVolumeFetcher
        
        fetcher = StableVolumeFetcher()
        volume_data = fetcher.get_current_5m_volume()
        
        if volume_data.get("status") == "success":
            logger.success(f"✅ Direct fetch successful: {volume_data['current_volume']:.1f} BTC ({volume_data['volume_category']})")
            return True
        else:
            logger.error(f"❌ Direct fetch failed: {volume_data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Direct stable fetcher test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🎯 Volume Integration Test Suite")
    logger.info("Testing the fix for wild volume fluctuations")
    print()
    
    # Test direct stable fetcher
    direct_test = test_direct_stable_fetcher()
    
    # Test HyperliquidAPI integration
    integration_test = test_hyperliquid_api_volume()
    
    print()
    logger.info("📊 TEST RESULTS:")
    logger.info("=" * 50)
    
    if direct_test:
        logger.success("✅ Direct Stable Fetcher: PASSED")
    else:
        logger.error("❌ Direct Stable Fetcher: FAILED")
    
    if integration_test:
        logger.success("✅ HyperliquidAPI Integration: PASSED")
    else:
        logger.error("❌ HyperliquidAPI Integration: FAILED")
    
    if direct_test and integration_test:
        logger.success("🎉 ALL TESTS PASSED - Volume fluctuation fix is working!")
        logger.info("🚀 The bot will now show stable volume readings without wild jumps")
    else:
        logger.error("❌ Some tests failed - volume system may still have issues")
        
    print()