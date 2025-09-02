#!/usr/bin/env python3
"""
System Initializer Service
Handles all system initialization and setup
Single Responsibility: System setup and connections
"""

import os
import time
from typing import Dict, Any
from loguru import logger
from core.api.hyperliquid_api import HyperliquidAPI
from core.api.hyperliquid_websocket import HyperliquidWebSocket
from core.api.hyperliquid_simulator import HyperliquidSimulator
from core.market_data_manager import market_data_manager
from core.constants import technical_constants

class SystemInitializer:
    """System initialization service - handles setup and connections"""
    
    def __init__(self, config):
        self.config = config
        self.connected = False
        
        logger.info("⚙️ System Initializer initialized - Setup coordination")
    
    def initialize_system(self, market_data_service) -> Dict[str, Any]:
        """Initialize all system components"""
        try:
            # Ensure environment
            self._ensure_env_file()
            
            # Initialize APIs and connections
            connection_result = self.connect()
            if not connection_result["success"]:
                return {"success": False, "error": "Failed to connect to APIs"}
            
            # Initialize market data
            market_data_service.initialize_yahoo_rsi()
            
            # Initialize candle buffers
            self._initialize_candle_buffers()
            
            # Test API connections
            test_result = self._test_api_connections(connection_result["hyperliquid_api"])
            
            # Initialize simulator
            hyperliquid_simulator = HyperliquidSimulator()
            
            return {
                "success": True,
                "hyperliquid_api": connection_result["hyperliquid_api"],
                "hyperliquid_websocket": connection_result["hyperliquid_websocket"],
                "hyperliquid_simulator": hyperliquid_simulator,
                "connection_test": test_result
            }
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def connect(self) -> Dict[str, Any]:
        """Connect to Hyperliquid API and start WebSocket"""
        try:
            # Initialize Hyperliquid API
            try:
                hyperliquid_api = HyperliquidAPI()
                logger.info("✅ Connected to Hyperliquid API")
            except Exception as e:
                logger.error(f"❌ Failed to create HyperliquidAPI instance: {e}")
                return {"success": False, "error": str(e)}
            
            # Initialize WebSocket
            hyperliquid_websocket = self._initialize_websocket()
            
            self.connected = True
            return {
                "success": True,
                "hyperliquid_api": hyperliquid_api,
                "hyperliquid_websocket": hyperliquid_websocket
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_websocket(self) -> HyperliquidWebSocket:
        """Initialize Hyperliquid WebSocket for real-time price updates"""
        try:
            hyperliquid_websocket = HyperliquidWebSocket(symbol="BTC")
            
            # Start WebSocket
            hyperliquid_websocket.start()
            logger.info("🔴 Starting Hyperliquid WebSocket connection...")
            
            # Wait for initial connection
            time.sleep(3)
            
            if hyperliquid_websocket.is_connected():
                logger.success("🔴 WebSocket connected - REAL-TIME PRICE STREAM ACTIVE")
            else:
                logger.warning("⚠️ WebSocket connection failed - using HTTP API fallback")
            
            return hyperliquid_websocket
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebSocket: {e}")
            return None
    
    def _initialize_candle_buffers(self):
        """Initialize candle buffer management"""
        try:
            # Clear market data manager cache for fresh data
            market_data_manager.clear_cache("market_data")
            logger.info("🧹 Market data cache cleared for fresh session")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize candle buffers: {e}")
    
    def _ensure_env_file(self):
        """Ensure .env file exists with complete configuration from template"""
        env_file = ".env"
        env_example = "env_example.txt"
        
        if not os.path.exists(env_file):
            logger.warning("⚠️ .env file not found, creating from template...")
            try:
                # Copy complete template if it exists
                if os.path.exists(env_example):
                    import shutil
                    shutil.copy2(env_example, env_file)
                    logger.info("📝 Complete .env file created from env_example.txt")
                    logger.warning("⚠️ Please configure wallet credentials and adjust settings in .env")
                else:
                    # Fallback: create basic template
                    with open(env_file, 'w') as f:
                        f.write("# HyperLBot Configuration\n")
                        f.write("WALLET_ADDRESS=your_wallet_address\n")
                        f.write("WALLET_PRIVATE_KEY=your_private_key\n")
                        f.write("TRADING_MODE=paper\n")
                        f.write("LOG_LEVEL=INFO\n")
                        f.write("DASHBOARD_PORT=5002\n")
                    logger.info("📝 Basic .env file created - please configure your settings")
            except Exception as e:
                logger.error(f"❌ Could not create .env file: {e}")
    
    def _test_api_connections(self, hyperliquid_api) -> Dict[str, Any]:
        """Test API connections"""
        test_results = {"yahoo_finance": False, "hyperliquid_api": False}
        
        try:
            # Test Yahoo Finance connection
            from core.analysis.historical.historical_data_coordinator import MarketDataAnalyzer
            test_analyzer = MarketDataAnalyzer()
            if test_analyzer.test_connection():
                test_results["yahoo_finance"] = True
                logger.success("✅ Yahoo Finance connection test passed")
            else:
                logger.error("❌ Yahoo Finance connection test failed")
        except Exception as e:
            logger.error(f"❌ Yahoo Finance test error: {e}")
        
        try:
            # Test Hyperliquid API connection
            if hyperliquid_api:
                current_price = hyperliquid_api.get_current_price("BTC")
                if current_price and current_price > 0:
                    test_results["hyperliquid_api"] = True
                    logger.success(f"✅ Hyperliquid API connected - BTC: ${current_price:,.2f}")
                else:
                    logger.error("❌ Hyperliquid API connection test failed")
        except Exception as e:
            logger.error(f"❌ Hyperliquid API test error: {e}")
        
        return test_results