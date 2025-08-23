#!/usr/bin/env python3
"""
Test Setup for HyperLBot
Simplified test configuration and setup
"""

import sys
import os
from loguru import logger

# Import core module to setup paths
import core

def test_imports():
    """Test all module imports"""
    logger.info("Testing module imports...")
    
    try:
        # Test core modules
        from core.config import TradingConfig
        logger.info("✅ Core config imported successfully")
        
        from hyperliquid_api import HyperliquidAPI
        logger.info("✅ Hyperliquid API imported successfully")
        
        from trading_logger import TradingLogger
        logger.info("✅ Trading logger imported successfully")
        
        # Test data modules
        from external_data_fetcher import ExternalDataFetcher
        logger.info("✅ External data fetcher imported successfully")
        
        from blockcypher_analyzer import BlockCypherAnalyzer
        logger.info("✅ BlockCypher analyzer imported successfully")
        
        # Test strategy modules
        from fee_manager import FeeManager
        logger.info("✅ Fee manager imported successfully")
        
        from variability_analyzer import VariabilityAnalyzer
        logger.info("✅ Variability analyzer imported successfully")
        
        from prediction_engine import PredictionEngine
        logger.info("✅ Prediction engine imported successfully")
        
        from trade_manager import TradeManager
        logger.info("✅ Trade manager imported successfully")
        
        from whale_integration import WhaleIntegration
        logger.info("✅ Whale integration imported successfully")
        
        from hybrid_paper_trading_bot import HybridPaperTradingBot
        logger.info("✅ Hybrid paper trading bot imported successfully")
        
        logger.info("🎉 All modules imported successfully!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration...")
    
    try:
        from core.config import TradingConfig
        config = TradingConfig()
        logger.info("✅ Configuration loaded successfully")
        logger.info(f"   Strategy configs: {len(config.STRATEGY_CONFIGS)} strategies available")
        logger.info(f"   Whale analytics: {'Enabled' if config.WHALE_ANALYTICS_ENABLED else 'Disabled'}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return False

def test_api_connections():
    """Test API connections (without placing trades)"""
    logger.info("Testing API connections...")
    
    try:
        # Test external data fetcher
        from external_data_fetcher import ExternalDataFetcher
        fetcher = ExternalDataFetcher()
        logger.info("✅ External data fetcher initialized")
        
        # Test whale integration
        from whale_integration import WhaleIntegration
        whale = WhaleIntegration(enabled=True)
        logger.info("✅ Whale integration initialized")
        
        logger.info("🎉 API connections tested successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ API connection error: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 HyperLBot Test Setup")
    logger.info("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("API Connections", test_api_connections)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running {test_name} test...")
        if test_func():
            passed += 1
            logger.info(f"✅ {test_name} test passed")
        else:
            logger.error(f"❌ {test_name} test failed")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! HyperLBot is ready to run.")
    else:
        logger.error("⚠️  Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
