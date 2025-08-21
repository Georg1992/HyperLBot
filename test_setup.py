#!/usr/bin/env python3
"""
Test script to verify HyperLBot setup and basic functionality
"""

import sys
import os
from loguru import logger

# Import core module to setup paths
import core

def test_imports():
    """Test that all modules can be imported"""
    logger.info("🔍 Testing imports...")
    
    try:
        # Test core imports
        from config import TradingConfig
        logger.success("✅ Config imported successfully")
        
        from hyperliquid_api import HyperliquidAPI
        logger.success("✅ HyperliquidAPI imported successfully")
        
        from trading_logger import TradingLogger
        logger.success("✅ TradingLogger imported successfully")
        
        # Test data imports
        from external_data_fetcher import ExternalDataFetcher
        logger.success("✅ ExternalDataFetcher imported successfully")
        
        # Test strategy imports
        from fee_manager import FeeManager
        logger.success("✅ FeeManager imported successfully")
        
        from variability_analyzer import VariabilityAnalyzer
        logger.success("✅ VariabilityAnalyzer imported successfully")
        
        from hybrid_paper_trading_bot import HybridPaperTradingBot
        logger.success("✅ HybridPaperTradingBot imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of components"""
    logger.info("🔍 Testing basic functionality...")
    
    try:
        # Test config
        from config import TradingConfig
        config = TradingConfig()
        logger.success("✅ Config initialization successful")
        
        # Test fee manager
        from fee_manager import FeeManager
        fee_manager = FeeManager()
        fees = fee_manager.calculate_order_fees(0.001, 50000, "LIMIT")
        logger.success(f"✅ Fee calculation successful: ${fees['total_cost']:.4f}")
        
        # Test variability analyzer
        from variability_analyzer import VariabilityAnalyzer
        analyzer = VariabilityAnalyzer(lookback_periods=10)
        analyzer.add_price_data(50000.0, volume=1000)
        analysis = analyzer.get_variability_analysis()
        logger.success("✅ Variability analyzer test successful")
        
        # Test trading logger
        from trading_logger import TradingLogger
        trading_logger = TradingLogger("test_logs")
        logger.success("✅ Trading logger initialization successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic functionality test failed: {e}")
        return False

def test_external_data_fetcher():
    """Test external data fetcher (requires internet)"""
    logger.info("🔍 Testing external data fetcher...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))
        from external_data_fetcher import ExternalDataFetcher
        
        fetcher = ExternalDataFetcher()
        
        # Test connection
        if fetcher.test_connection():
            logger.success("✅ Binance API connection successful")
            
            # Test market analysis
            analysis = fetcher.get_market_analysis("BTCUSDT")
            if "error" not in analysis:
                logger.success(f"✅ Market analysis successful: ${analysis['current_price']:,.2f}")
                return True
            else:
                logger.warning(f"⚠️ Market analysis failed: {analysis['error']}")
                return False
        else:
            logger.error("❌ Binance API connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ External data fetcher test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 HyperLBot Setup Test")
    logger.info("=" * 50)
    
    # Test imports
    if not test_imports():
        logger.error("❌ Import tests failed. Check your installation.")
        return False
    
    # Test basic functionality
    if not test_basic_functionality():
        logger.error("❌ Basic functionality tests failed.")
        return False
    
    # Test external data fetcher (optional - requires internet)
    logger.info("🌐 Testing external data fetcher (requires internet connection)...")
    if test_external_data_fetcher():
        logger.success("✅ All tests passed! Your HyperLBot setup is ready.")
    else:
        logger.warning("⚠️ External data fetcher test failed, but core functionality is working.")
        logger.info("💡 You can still use the bot for paper trading and analysis.")
    
    logger.info("=" * 50)
    logger.info("🎯 Next steps:")
    logger.info("1. Set up your .env file with wallet credentials")
    logger.info("2. Run 'python main.py' to start the bot")
    logger.info("3. Test with paper trading first")
    
    return True

if __name__ == "__main__":
    main()
