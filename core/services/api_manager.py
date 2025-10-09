#!/usr/bin/env python3
"""
API Manager - Centralized management of all external APIs and WebSockets
Manages 7 APIs/WebSockets: HyperliquidAPI, BinanceAPI, FearGreedAPI, WhaleAnalyticsAPI, 
RSSNewsAPI, HyperliquidWebSocket, BinanceWebSocket
"""

import time
from typing import Dict, Any, Optional
from loguru import logger

class APIManager:
    """Centralized management of all external APIs and WebSockets"""
    
    def __init__(self):
        # APIs
        self.hyperliquid_api = None
        self.binance_api = None
        self.fear_greed_api = None
        self.whale_analytics_api = None
        self.rss_news_api = None
        
        # WebSockets
        self.hyperliquid_websocket = None
        self.binance_websocket = None
        
        # Initialization status
        self.initialized = False
        self.initialization_results = {}
        
        logger.info("🔌 API Manager created")
    
    def initialize_all(self) -> Dict[str, Any]:
        """Initialize all APIs and WebSockets"""
        try:
            logger.info("🚀 Initializing all APIs and WebSockets...")
            
            # Initialize APIs
            api_results = self._initialize_apis()
            if not api_results["success"]:
                return {"success": False, "error": "API initialization failed"}
            
            # Initialize WebSockets
            websocket_results = self._initialize_websockets()
            if not websocket_results["success"]:
                return {"success": False, "error": "WebSocket initialization failed"}
            
            # Test all connections
            test_results = self._test_all_connections()
            if not test_results["success"]:
                return {"success": False, "error": "Connection testing failed"}
            
            self.initialized = True
            logger.success("✅ All APIs and WebSockets initialized successfully")
            
            return {
                "success": True,
                "apis": {
                    "hyperliquid_api": self.hyperliquid_api,
                    "binance_api": self.binance_api,
                    "fear_greed_api": self.fear_greed_api,
                    "whale_analytics_api": self.whale_analytics_api,
                    "rss_news_api": self.rss_news_api
                },
                "websockets": {
                    "hyperliquid_websocket": self.hyperliquid_websocket,
                    "binance_websocket": self.binance_websocket
                },
                "initialization_results": self.initialization_results
            }
            
        except Exception as e:
            logger.error(f"❌ API Manager initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_apis(self) -> Dict[str, Any]:
        """Initialize all APIs"""
        try:
            logger.info("📡 Initializing APIs...")
            
            # 1. Hyperliquid API
            from core.api.hyperliquid_api import get_hyperliquid_api
            self.hyperliquid_api = get_hyperliquid_api()
            self.initialization_results["hyperliquid_api"] = "✅ Initialized"
            
            # 2. Binance API
            from core.external.binance_api import get_global_binance_api
            self.binance_api = get_global_binance_api()
            self.initialization_results["binance_api"] = "✅ Initialized"
            
            # 3. Fear & Greed API
            from core.external.fear_greed_api import get_global_fear_greed_api
            self.fear_greed_api = get_global_fear_greed_api()
            self.initialization_results["fear_greed_api"] = "✅ Initialized"
            
            # 4. Whale Analytics API
            from core.external.whale_analytics_api import get_global_whale_analytics_api
            self.whale_analytics_api = get_global_whale_analytics_api()
            self.initialization_results["whale_analytics_api"] = "✅ Initialized"
            
            # 5. RSS News API
            from core.external.rss_news_api import get_global_rss_news_api
            self.rss_news_api = get_global_rss_news_api()
            self.initialization_results["rss_news_api"] = "✅ Initialized"
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ API initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_websockets(self) -> Dict[str, Any]:
        """Initialize all WebSockets"""
        try:
            logger.info("🔌 Initializing WebSockets...")
            
            # 1. Hyperliquid WebSocket
            from core.api.hyperliquid_websocket import get_websocket_instance
            self.hyperliquid_websocket = get_websocket_instance("BTC")
            self.hyperliquid_websocket.start()
            self.initialization_results["hyperliquid_websocket"] = "✅ Started"
            
            # 2. Binance WebSocket
            from core.external.binance_websocket import get_binance_websocket
            self.binance_websocket = get_binance_websocket("BTCUSDT")
            self.binance_websocket.start()
            self.initialization_results["binance_websocket"] = "✅ Started"
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ WebSocket initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _test_all_connections(self) -> Dict[str, Any]:
        """Test all API and WebSocket connections"""
        try:
            logger.info("🧪 Testing all connections...")
            
            # Wait for WebSocket to be ready before testing
            logger.info("⏳ Waiting for WebSocket connections to establish...")
            import time
            time.sleep(3)  # Give WebSocket time to connect
            
            # Test Hyperliquid API
            current_price = self.hyperliquid_api.get_current_price("BTC")
            if not current_price:
                return {"success": False, "error": "Hyperliquid API connection failed"}
            logger.success(f"✅ Hyperliquid API: BTC ${current_price:,.2f}")
            
            # Test Hyperliquid WebSocket (wait for connection)
            import time
            max_wait = 10  # 10 seconds max wait
            wait_time = 0
            while not self.hyperliquid_websocket.is_connected() and wait_time < max_wait:
                time.sleep(0.5)
                wait_time += 0.5
            
            if not self.hyperliquid_websocket.is_connected():
                logger.warning("⚠️ Hyperliquid WebSocket not connected yet, but continuing...")
            
            # Test Binance WebSocket (wait for connection)
            wait_time = 0
            while not self.binance_websocket.is_connected() and wait_time < max_wait:
                time.sleep(0.5)
                wait_time += 0.5
            
            if not self.binance_websocket.is_connected():
                logger.warning("⚠️ Binance WebSocket not connected yet, but continuing...")
            
            # Test other APIs (optional - they might fail without affecting core functionality)
            try:
                fear_greed_data = self.fear_greed_api.get_fear_greed_index()
                logger.success("✅ Fear & Greed API working")
            except Exception as e:
                logger.warning(f"⚠️ Fear & Greed API test failed: {e}")
            
            try:
                whale_data = self.whale_analytics_api.get_whale_analytics()
                logger.success("✅ Whale Analytics API working")
            except Exception as e:
                logger.warning(f"⚠️ Whale Analytics API test failed: {e}")
            
            try:
                news_data = self.rss_news_api.get_news_sentiment()
                logger.success("✅ RSS News API working")
            except Exception as e:
                logger.warning(f"⚠️ RSS News API test failed: {e}")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Connection testing failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_api(self, api_name: str):
        """Get specific API instance"""
        if not self.initialized:
            raise Exception("API Manager not initialized")
        
        api_map = {
            "hyperliquid_api": self.hyperliquid_api,
            "binance_api": self.binance_api,
            "fear_greed_api": self.fear_greed_api,
            "whale_analytics_api": self.whale_analytics_api,
            "rss_news_api": self.rss_news_api
        }
        
        if api_name not in api_map:
            raise ValueError(f"Unknown API: {api_name}")
        
        return api_map[api_name]
    
    def get_websocket(self, websocket_name: str):
        """Get specific WebSocket instance"""
        if not self.initialized:
            raise Exception("API Manager not initialized")
        
        websocket_map = {
            "hyperliquid_websocket": self.hyperliquid_websocket,
            "binance_websocket": self.binance_websocket
        }
        
        if websocket_name not in websocket_map:
            raise ValueError(f"Unknown WebSocket: {websocket_name}")
        
        return websocket_map[websocket_name]
    
    def stop_all_websockets(self):
        """Stop all WebSocket connections"""
        try:
            if self.hyperliquid_websocket:
                self.hyperliquid_websocket.stop()
                logger.info("🛑 Hyperliquid WebSocket stopped")
            
            if self.binance_websocket:
                self.binance_websocket.stop()
                logger.info("🛑 Binance WebSocket stopped")
                
        except Exception as e:
            logger.error(f"❌ Error stopping WebSockets: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all APIs and WebSockets"""
        return {
            "initialized": self.initialized,
            "apis": {
                "hyperliquid_api": self.hyperliquid_api is not None,
                "binance_api": self.binance_api is not None,
                "fear_greed_api": self.fear_greed_api is not None,
                "whale_analytics_api": self.whale_analytics_api is not None,
                "rss_news_api": self.rss_news_api is not None
            },
            "websockets": {
                "hyperliquid_websocket": self.hyperliquid_websocket.is_connected() if self.hyperliquid_websocket else False,
                "binance_websocket": self.binance_websocket.is_connected() if self.binance_websocket else False
            },
            "initialization_results": self.initialization_results
        }

# Global API Manager instance
_global_api_manager = None

def get_global_api_manager() -> APIManager:
    """Get the global API Manager singleton instance"""
    global _global_api_manager
    if _global_api_manager is None:
        _global_api_manager = APIManager()
    return _global_api_manager
