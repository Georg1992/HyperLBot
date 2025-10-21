#!/usr/bin/env python3
"""
Market Data Service - Simplified Architecture
Single Responsibility: Market data coordination
Clean, simple data hub for all market data needs
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger

class MarketDataService:
    """Simplified market data service - direct API calls, simple caching"""
    
    def __init__(self, hyperliquid_api, hyperliquid_websocket, binance_api=None):
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        self.binance_api = binance_api
        
        # Simple caching
        self._cache = {}
        self._cache_timestamps = {}
        
        logger.info("📊 Market Data Service initialized - Simple data hub")
    
    # ==================================================================================
    # SIMPLE, DIRECT API METHODS - No complex inheritance or caching
    # ==================================================================================
    
    def get_historical_candles(self, symbol: str = "BTC", interval: str = "5m", limit: int = 20) -> List[Dict[str, Any]]:
        """Get historical candles - direct API call with simple caching"""
        try:
            cache_key = f"candles_{symbol}_{interval}_{limit}"
            
            # Check simple cache
            if self._is_cache_valid(cache_key, 300):  # 5 minute cache
                logger.debug(f"📊 Using cached candles for {symbol} {interval}")
                return self._cache[cache_key]
            
            # Direct API call
            candles = self.hyperliquid_api.get_historical_candles(symbol, interval, limit)
            
            if candles:
                # Simple cache
                self._cache[cache_key] = candles
                self._cache_timestamps[cache_key] = time.time()
                logger.debug(f"📊 Fetched {len(candles)} {interval} candles for {symbol}")
                return candles
            else:
                logger.warning(f"⚠️ No candles returned for {symbol} {interval}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to get historical candles: {e}")
            return []
    
    def get_current_price(self) -> Optional[float]:
        """Get current price from WebSocket - direct call"""
        try:
            if self.hyperliquid_websocket and self.hyperliquid_websocket.is_connected():
                return self.hyperliquid_websocket.get_current_price()
            else:
                # Fallback to API using configured symbol
                from config.config import TradingConfig
                return self.hyperliquid_api.get_current_price(TradingConfig.SYMBOL)
        except Exception as e:
            logger.error(f"❌ Failed to get current price: {e}")
            return None
    
    def get_ongoing_candle(self, symbol: str = "BTC", interval: str = "5m") -> Optional[Dict[str, Any]]:
        """Get ongoing candle - direct API call"""
        try:
            return self.hyperliquid_api.get_ongoing_candle(symbol, interval)
        except Exception as e:
            logger.error(f"❌ Failed to get ongoing candle: {e}")
            return None
    
    def get_hyperliquid_price(self, symbol: str = None) -> Optional[float]:
        """Get current price from Hyperliquid - direct API call"""
        if symbol is None:
            # Use configured symbol from config
            from config.config import TradingConfig
            symbol = TradingConfig.SYMBOL
        
        # For now, just use the existing method (uses config)
        # When we add multi-symbol support, we'll use the symbol parameter
        return self.get_current_price()
    
    def get_hyperliquid_analysis(self, current_price: float) -> Dict[str, Any]:
        """Get comprehensive Hyperliquid market analysis"""
        try:
            # Get market data from API
            market_data = self.get_market_data()
            
            # Get current price if not provided
            if not current_price:
                current_price = self.get_current_price()
            
            # Get historical candles for analysis
            candles_5m = self.get_historical_candles("BTC", "5m", 20)
            candles_1h = self.get_historical_candles("BTC", "1h", 24)
            
            return {
                "current_price": current_price,
                "market_data": market_data,
                "candles_5m": candles_5m,
                "candles_1h": candles_1h,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid analysis: {e}")
            return {"error": str(e)}
    
    def get_current_5m_volume(self) -> float:
        """Get current 5m volume - direct API call"""
        try:
            recent_trades = self.hyperliquid_api.get_recent_trades("BTC", 100)
            if recent_trades:
                total_volume = sum(float(trade.get('sz', 0)) for trade in recent_trades)
                return total_volume
            return 0.0
        except Exception as e:
            logger.error(f"❌ Failed to get current 5m volume: {e}")
            return 0.0
    
    def get_market_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get market data - direct API call"""
        try:
            return self.hyperliquid_api.get_market_data(symbol)
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {}
    
    def get_recent_trades(self, symbol: str = "BTC", limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades - direct API call"""
        try:
            return self.hyperliquid_api.get_recent_trades(symbol, limit)
        except Exception as e:
            logger.error(f"❌ Failed to get recent trades: {e}")
            return []
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get current data update status"""
        return {
            "hyperliquid_connected": True,
            "websocket_connected": self.hyperliquid_websocket.is_connected() if self.hyperliquid_websocket else False,
            "last_update": time.time()
        }
    
    def _is_cache_valid(self, key: str, duration: int = 300) -> bool:
        """Simple cache validation"""
        if key not in self._cache or key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[key] < duration
    
    def invalidate_cache(self, symbol: str = "BTC", interval: str = None):
        """Invalidate cache for specific symbol/interval or all"""
        try:
            if interval:
                # Invalidate specific interval
                keys_to_remove = [key for key in self._cache.keys() if f"{symbol}_{interval}" in key]
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)
                logger.info(f"🗑️ Invalidated {interval} cache for {symbol}")
            else:
                # Invalidate all cache
                self._cache.clear()
                self._cache_timestamps.clear()
                logger.info("🗑️ Invalidated all cache")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache: {e}")

# Global instance
_global_market_data_service = None

def get_global_market_data_service() -> MarketDataService:
    """Get the global MarketDataService singleton instance"""
    global _global_market_data_service
    if _global_market_data_service is None:
        # This will be set by SystemInitializer
        logger.warning("⚠️ MarketDataService not initialized - call SystemInitializer first")
    return _global_market_data_service

def set_global_market_data_service(service: MarketDataService):
    """Set the global MarketDataService instance"""
    global _global_market_data_service
    _global_market_data_service = service
    logger.info("📊 Global MarketDataService instance set")