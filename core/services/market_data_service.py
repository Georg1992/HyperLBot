#!/usr/bin/env python3
"""
Market Data Service - Smart Data Flow Architecture
Single Responsibility: Efficient market data coordination with smart caching
Optimized for single bot with multiple consumers (prediction, UI)
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger

class MarketDataService:
    """Smart market data service - intelligent caching, batch fetching, optimized data flow"""
    
    def __init__(self, hyperliquid_api, hyperliquid_websocket, binance_api=None):
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        self.binance_api = binance_api
        
        # Smart caching with metric-specific schedules
        self._cache = {}
        self._cache_timestamps = {}
        self._update_schedules = {
            "price": 1,           # 1 second - real-time
            "candles_1m": 60,     # 1 minute
            "candles_5m": 300,    # 5 minutes
            "candles_1h": 3600,   # 1 hour
            "candles_1d": 86400,  # 1 day
            "volume": 60,          # 1 minute
            "market_data": 300,    # 5 minutes
            "trades": 30           # 30 seconds
        }
        
        # Data flow optimization
        self._last_batch_fetch = 0
        self._batch_interval = 5  # Batch fetch every 5 seconds
        
        logger.info("📊 Smart Market Data Service initialized - Optimized data flow")
    
    # ==================================================================================
    # SMART CACHING METHODS - Intelligent data management
    # ==================================================================================
    
    def _get_cache_key(self, metric: str, symbol: str = "BTC", **kwargs) -> str:
        """Generate cache key for metric with parameters"""
        params = "_".join(f"{k}_{v}" for k, v in sorted(kwargs.items()))
        return f"{metric}_{symbol}_{params}" if params else f"{metric}_{symbol}"
    
    def _is_cache_valid(self, cache_key: str, custom_duration: int = None) -> bool:
        """Check if cache is valid based on metric-specific schedule"""
        if cache_key not in self._cache or cache_key not in self._cache_timestamps:
            return False
        
        # Use custom duration or metric-specific schedule
        if custom_duration:
            duration = custom_duration
        else:
            # Extract metric from cache key
            metric = cache_key.split("_")[0]
            duration = self._update_schedules.get(metric, 300)  # Default 5 minutes
        
        return time.time() - self._cache_timestamps[cache_key] < duration
    
    def _cache_data(self, cache_key: str, data: Any) -> None:
        """Cache data with timestamp"""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
        logger.debug(f"📊 Cached {cache_key}")
    
    def _get_cached_data(self, cache_key: str) -> Any:
        """Get cached data if valid"""
        if self._is_cache_valid(cache_key):
            logger.debug(f"📊 Using cached data: {cache_key}")
            return self._cache[cache_key]
        return None
    
    # ==================================================================================
    # BATCH DATA FETCHING - Reduce API calls, improve efficiency
    # ==================================================================================
    
    def get_batch_market_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Fetch all market data in one optimized batch - reduces API calls"""
        try:
            current_time = time.time()
            
            # Check if we should batch fetch (every 5 seconds)
            if current_time - self._last_batch_fetch < self._batch_interval:
                logger.debug("📊 Using recent batch data")
                return self._get_cached_batch_data()
            
            logger.info("📊 Fetching batch market data...")
            
            # Batch fetch all data
            batch_data = {
                "price": self._fetch_current_price(),
                "candles_1m": self._fetch_candles(symbol, "1m", 20),
                "candles_5m": self._fetch_candles(symbol, "5m", 30),
                "candles_1h": self._fetch_candles(symbol, "1h", 24),
                "candles_1d": self._fetch_candles(symbol, "1d", 7),
                "volume": self._fetch_volume_data(),
                "market_data": self._fetch_market_data(symbol),
                "trades": self._fetch_recent_trades(symbol, 50),
                "timestamp": current_time
            }
            
            # Cache batch data
            batch_key = f"batch_{symbol}"
            self._cache_data(batch_key, batch_data)
            self._last_batch_fetch = current_time
            
            logger.info("📊 Batch market data fetched and cached")
            return batch_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch batch market data: {e}")
            return self._get_cached_batch_data() or {}
    
    def _get_cached_batch_data(self) -> Optional[Dict[str, Any]]:
        """Get cached batch data if available"""
        batch_key = "batch_BTC"  # Default symbol
        return self._get_cached_data(batch_key)
    
    # ==================================================================================
    # OPTIMIZED INDIVIDUAL METHODS - Smart caching with metric-specific schedules
    # ==================================================================================
    
    def get_historical_candles(self, symbol: str = "BTC", interval: str = "5m", limit: int = 20) -> List[Dict[str, Any]]:
        """Get historical candles - smart caching with interval-specific schedules"""
        try:
            cache_key = self._get_cache_key("candles", symbol, interval=interval, limit=limit)
            
            # Check smart cache
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Fetch new data
            candles = self.hyperliquid_api.get_historical_candles(symbol, interval, limit)
            
            if candles:
                self._cache_data(cache_key, candles)
                logger.debug(f"📊 Fetched {len(candles)} {interval} candles for {symbol}")
                return candles
            else:
                logger.warning(f"⚠️ No candles returned for {symbol} {interval}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to get historical candles: {e}")
            return []
    
    # ==================================================================================
    # HELPER METHODS FOR BATCH FETCHING - Internal data fetching
    # ==================================================================================
    
    def _fetch_current_price(self) -> Optional[float]:
        """Fetch current price - internal method"""
        try:
            if self.hyperliquid_websocket and self.hyperliquid_websocket.is_connected():
                return self.hyperliquid_websocket.get_current_price()
            else:
                from config.config import TradingConfig
                return self.hyperliquid_api.get_current_price(TradingConfig.SYMBOL)
        except Exception as e:
            logger.error(f"❌ Failed to fetch current price: {e}")
            return None
    
    def _fetch_candles(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch candles - internal method"""
        try:
            return self.hyperliquid_api.get_historical_candles(symbol, interval, limit)
        except Exception as e:
            logger.error(f"❌ Failed to fetch {interval} candles: {e}")
            return []
    
    def _fetch_volume_data(self) -> float:
        """Fetch volume data - internal method"""
        try:
            recent_trades = self.hyperliquid_api.get_recent_trades("BTC", 100)
            if recent_trades:
                return sum(float(trade.get('sz', 0)) for trade in recent_trades)
            return 0.0
        except Exception as e:
            logger.error(f"❌ Failed to fetch volume data: {e}")
            return 0.0
    
    def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data - internal method"""
        try:
            return self.hyperliquid_api.get_market_data(symbol)
        except Exception as e:
            logger.error(f"❌ Failed to fetch market data: {e}")
            return {}
    
    def _fetch_recent_trades(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch recent trades - internal method"""
        try:
            return self.hyperliquid_api.get_recent_trades(symbol, limit)
        except Exception as e:
            logger.error(f"❌ Failed to fetch recent trades: {e}")
            return []
    
    # ==================================================================================
    # OPTIMIZED PUBLIC METHODS - Smart caching with metric-specific schedules
    # ==================================================================================
    
    def get_current_price(self) -> Optional[float]:
        """Get current price - smart caching (1 second)"""
        try:
            cache_key = self._get_cache_key("price")
            cached_price = self._get_cached_data(cache_key)
            if cached_price is not None:
                return cached_price
            
            # Fetch new price
            price = self._fetch_current_price()
            if price is not None:
                self._cache_data(cache_key, price)
            return price
        except Exception as e:
            logger.error(f"❌ Failed to get current price: {e}")
            return None
    
    def get_ongoing_candle(self, symbol: str = "BTC", interval: str = "5m") -> Optional[Dict[str, Any]]:
        """Get ongoing candle - smart caching (1 minute)"""
        try:
            cache_key = self._get_cache_key("ongoing_candle", symbol, interval=interval)
            cached_candle = self._get_cached_data(cache_key)
            if cached_candle is not None:
                return cached_candle
            
            # Fetch new candle
            candle = self.hyperliquid_api.get_ongoing_candle(symbol, interval)
            if candle:
                self._cache_data(cache_key, candle)
            return candle
        except Exception as e:
            logger.error(f"❌ Failed to get ongoing candle: {e}")
            return None
    
    def get_hyperliquid_price(self, symbol: str = None) -> Optional[float]:
        """Get current price from Hyperliquid - uses smart caching"""
        if symbol is None:
            from config.config import TradingConfig
            symbol = TradingConfig.SYMBOL
        
        # Use the smart cached get_current_price method
        return self.get_current_price()
    
    def get_current_5m_volume(self) -> float:
        """Get current 5m volume - smart caching (1 minute)"""
        try:
            cache_key = self._get_cache_key("volume")
            cached_volume = self._get_cached_data(cache_key)
            if cached_volume is not None:
                return cached_volume
            
            # Fetch new volume
            volume = self._fetch_volume_data()
            self._cache_data(cache_key, volume)
            return volume
        except Exception as e:
            logger.error(f"❌ Failed to get current 5m volume: {e}")
            return 0.0
    
    def get_market_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get market data - smart caching (5 minutes)"""
        try:
            cache_key = self._get_cache_key("market_data", symbol)
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Fetch new market data
            market_data = self._fetch_market_data(symbol)
            if market_data:
                self._cache_data(cache_key, market_data)
            return market_data
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {}
    
    def get_recent_trades(self, symbol: str = "BTC", limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades - smart caching (30 seconds)"""
        try:
            cache_key = self._get_cache_key("trades", symbol, limit=limit)
            cached_trades = self._get_cached_data(cache_key)
            if cached_trades is not None:
                return cached_trades
            
            # Fetch new trades
            trades = self._fetch_recent_trades(symbol, limit)
            if trades:
                self._cache_data(cache_key, trades)
            return trades
        except Exception as e:
            logger.error(f"❌ Failed to get recent trades: {e}")
            return []
    
    # ==================================================================================
    # DATA FLOW OPTIMIZATION - Pre-processed data packages for consumers
    # ==================================================================================
    
    def get_prediction_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get optimized data package for prediction engine"""
        try:
            # Use batch data if available, otherwise fetch individually
            batch_data = self._get_cached_batch_data()
            if batch_data:
                return {
                    "price": batch_data.get("price"),
                    "candles_5m": batch_data.get("candles_5m", []),
                    "candles_1h": batch_data.get("candles_1h", []),
                    "candles_1d": batch_data.get("candles_1d", []),
                    "volume": batch_data.get("volume", 0.0),
                    "market_data": batch_data.get("market_data", {}),
                    "timestamp": batch_data.get("timestamp", time.time())
                }
            else:
                # Fallback to individual fetches
                return {
                    "price": self.get_current_price(),
                    "candles_5m": self.get_historical_candles(symbol, "5m", 30),
                    "candles_1h": self.get_historical_candles(symbol, "1h", 24),
                    "candles_1d": self.get_historical_candles(symbol, "1d", 7),
                    "volume": self.get_current_5m_volume(),
                    "market_data": self.get_market_data(symbol),
                    "timestamp": time.time()
                }
        except Exception as e:
            logger.error(f"❌ Failed to get prediction data: {e}")
            return {}
    
    def get_dashboard_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get optimized data package for dashboard UI"""
        try:
            # Use batch data if available, otherwise fetch individually
            batch_data = self._get_cached_batch_data()
            if batch_data:
                return {
                    "price": batch_data.get("price"),
                    "candles_1m": batch_data.get("candles_1m", []),
                    "candles_5m": batch_data.get("candles_5m", []),
                    "volume": batch_data.get("volume", 0.0),
                    "trades": batch_data.get("trades", []),
                    "market_data": batch_data.get("market_data", {}),
                    "timestamp": batch_data.get("timestamp", time.time())
                }
            else:
                # Fallback to individual fetches
                return {
                    "price": self.get_current_price(),
                    "candles_1m": self.get_historical_candles(symbol, "1m", 20),
                    "candles_5m": self.get_historical_candles(symbol, "5m", 30),
                    "volume": self.get_current_5m_volume(),
                    "trades": self.get_recent_trades(symbol, 50),
                    "market_data": self.get_market_data(symbol),
                    "timestamp": time.time()
                }
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {}
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get current data update status with cache info"""
        return {
            "hyperliquid_connected": True,
            "websocket_connected": self.hyperliquid_websocket.is_connected() if self.hyperliquid_websocket else False,
            "last_batch_fetch": self._last_batch_fetch,
            "cache_size": len(self._cache),
            "cached_metrics": list(self._cache.keys()),
            "last_update": time.time()
        }
    
    def invalidate_cache(self, symbol: str = "BTC", interval: str = None, metric: str = None):
        """Smart cache invalidation - specific or all"""
        try:
            if metric:
                # Invalidate specific metric
                keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{metric}_")]
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)
                logger.info(f"🗑️ Invalidated {metric} cache")
            elif interval:
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
                self._last_batch_fetch = 0
                logger.info("🗑️ Invalidated all cache")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        try:
            current_time = time.time()
            cache_ages = {}
            
            for key, timestamp in self._cache_timestamps.items():
                age = current_time - timestamp
                cache_ages[key] = {
                    "age_seconds": round(age, 2),
                    "is_valid": self._is_cache_valid(key)
                }
            
            return {
                "total_cached_items": len(self._cache),
                "cache_ages": cache_ages,
                "update_schedules": self._update_schedules,
                "last_batch_fetch": self._last_batch_fetch,
                "batch_interval": self._batch_interval
            }
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {}

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