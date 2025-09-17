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
            # Check if already initialized to prevent duplicate API creation
            if self.connected:
                logger.info("⚙️ System already initialized, skipping duplicate initialization")
                # Return the existing API instances to maintain compatibility
                return {
                    "success": True, 
                    "already_initialized": True,
                    "hyperliquid_api": getattr(self, '_hyperliquid_api', None),
                    "hyperliquid_websocket": getattr(self, '_hyperliquid_websocket', None),
                    "hyperliquid_simulator": getattr(self, '_hyperliquid_simulator', None)
                }
            
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
            
            # Store API instances for future reuse
            self._hyperliquid_api = connection_result["hyperliquid_api"]
            self._hyperliquid_websocket = connection_result["hyperliquid_websocket"]
            self._hyperliquid_simulator = hyperliquid_simulator
            
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
        """Ensure .env file exists with interactive wallet credential setup"""
        env_file = ".env"
        env_example = "env_example.txt"
        
        if not os.path.exists(env_file):
            logger.warning("⚠️ .env file not found - Interactive setup required")
            print("\n" + "="*60)
            print("🔧 FIRST-TIME SETUP: Environment Configuration")
            print("="*60)
            
            try:
                # ALWAYS require wallet credentials first
                print("\n🔐 HYPERLIQUID WALLET CREDENTIALS REQUIRED:")
                print("💭 Wallet credentials are needed for ALL modes (market data + trading)")
                print("💭 Both paper trading and production need API access to Hyperliquid")
                print()
                
                # Validate wallet credentials are provided
                while True:
                    wallet_address = input("📍 Enter your Hyperliquid wallet address (REQUIRED): ").strip()
                    if wallet_address and wallet_address != "your_wallet_address_here":
                        print("   ✅ Wallet address accepted")
                        break
                    else:
                        print("   ❌ Wallet address is required for bot operation!")
                
                while True:
                    wallet_private_key = input("🔐 Enter your Hyperliquid private key (REQUIRED): ").strip()
                    if wallet_private_key and wallet_private_key != "your_private_key_here":
                        print("   ✅ Private key accepted")
                        break
                    else:
                        print("   ❌ Private key is required for bot operation!")
                
                # Trading mode selection AFTER credentials are validated
                print("\n⚙️ TRADING MODE SELECTION:")
                print("💡 Both modes use your wallet for market data access")
                print("1. Paper Trading (Simulated trades - Safe)")
                print("2. Production Trading (Real trades - Real money!)")
                
                while True:
                    mode_choice = input("Choose trading mode (1 or 2): ").strip()
                    if mode_choice == "1":
                        trading_mode = "paper"
                        print("   ✅ Paper trading mode selected (simulated trades)")
                        break
                    elif mode_choice == "2":
                        trading_mode = "production"
                        print("   ⚠️ Production mode selected (REAL MONEY!)")
                        break
                    else:
                        print("   ❌ Please enter 1 or 2")
                
                # Generate .env file
                if os.path.exists(env_example):
                    # Read template and replace placeholders
                    with open(env_example, 'r') as f:
                        template_content = f.read()
                    
                    # Replace placeholders with user input
                    env_content = template_content.replace(
                        "WALLET_ADDRESS=your_wallet_address_here", 
                        f"WALLET_ADDRESS={wallet_address}"
                    ).replace(
                        "WALLET_PRIVATE_KEY=your_private_key_here", 
                        f"WALLET_PRIVATE_KEY={wallet_private_key}"
                    ).replace(
                        "TRADING_MODE=paper", 
                        f"TRADING_MODE={trading_mode}"
                    )
                    
                    with open(env_file, 'w') as f:
                        f.write(env_content)
                    
                    logger.success("✅ Complete .env file created with your credentials!")
                else:
                    # Fallback: create basic template with user input
                    with open(env_file, 'w') as f:
                        f.write("# HyperLBot Configuration\n")
                        f.write(f"WALLET_ADDRESS={wallet_address}\n")
                        f.write(f"WALLET_PRIVATE_KEY={wallet_private_key}\n")
                        f.write(f"TRADING_MODE={trading_mode}\n")
                        f.write("LOG_LEVEL=INFO\n")
                        f.write("DASHBOARD_PORT=5002\n")
                    
                    logger.success("✅ Basic .env file created with your credentials!")
                
                print("\n🎯 SETUP COMPLETE!")
                print(f"📍 Configuration saved to: {env_file}")
                if trading_mode == "paper":
                    print("💡 You can start trading safely with paper trading mode")
                else:
                    print("⚠️ Production mode enabled - real money will be used!")
                print()
                
            except Exception as e:
                logger.error(f"❌ Error during interactive setup: {e}")
                # Create minimal fallback
                try:
                    with open(env_file, 'w') as f:
                        f.write("# HyperLBot Configuration\n")
                        f.write("WALLET_ADDRESS=your_wallet_address_here\n")
                        f.write("WALLET_PRIVATE_KEY=your_private_key_here\n")
                        f.write("TRADING_MODE=paper\n")
                    logger.info("📝 Fallback .env file created")
                except:
                    logger.error("❌ Could not create any .env file")
    
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