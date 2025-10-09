#!/usr/bin/env python3
"""
Market Data Service
Handles all market data orchestration and RSI management
Single Responsibility: Market data coordination
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger
from core.constants import technical_constants
from core.market_data_manager import get_global_market_data_manager
from core.data.base_data_manager import BaseDataManager

class MarketDataService(BaseDataManager):
    """Market data orchestration service - handles all data coordination"""
    
    def __init__(self, historical_data_coordinator, hyperliquid_api, hyperliquid_websocket, binance_api=None):
        # Initialize parent class (BaseDataManager) with caching
        super().__init__()
        
        self.historical_data_coordinator = historical_data_coordinator
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        self.binance_api = binance_api
        
        # Price caching for WebSocket
        self._cached_websocket_price = None
        self._last_price_update = 0
        
        # Override cache duration for different intervals
        self.cache_duration = 300  # 5 minutes default
        self._interval_cache_duration = {
            "1m": 60,    # 1 minute cache for 1m candles
            "5m": 300,   # 5 minute cache for 5m candles  
            "1h": 3600,  # 1 hour cache for 1h candles
            "1d": 86400  # 24 hour cache for 1d candles
        }
        
        logger.info("📊 Market Data Service initialized - Data orchestration with BaseDataManager caching")
    
    def initialize_hyperliquid_rsi(self):
        """Initialize Hyperliquid baseline RSI using RSICalculator"""
        try:
            # Get 5-minute data for RSI baseline calculation from Hyperliquid
            candles_5m = self.hyperliquid_api.get_historical_candles("BTC", "5m", 30)
            if candles_5m and len(candles_5m) >= 15:
                # Calculate baseline RSI using global RSICalculator (single source)
                from core.analysis.real_time.rsi_calculator import get_global_rsi_calculator
                rsi_calculator = get_global_rsi_calculator()
                rsi_value = rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m)
                logger.success(f"📊 Hyperliquid baseline RSI initialized: {rsi_value:.2f} (global RSI calculator)")
            else:
                logger.warning("⚠️ Not enough Hyperliquid 5m data for RSI baseline, using default")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Hyperliquid baseline RSI: {e}")
    
    def get_hyperliquid_price(self) -> Optional[float]:
        """Get current price from Hyperliquid API"""
        try:
            return self.hyperliquid_api.get_current_price("BTC")
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid price: {e}")
            return None
    
    def get_weekly_trend_analysis(self) -> Dict[str, Any]:
        """Get weekly trend analysis from Hyperliquid"""
        try:
            candles_1d = self.hyperliquid_api.get_historical_candles("BTC", "1d", 7)
            if candles_1d and len(candles_1d) >= 7:
                return {
                    "weekly_trend": "UP" if candles_1d[-1]["close"] > candles_1d[0]["close"] else "DOWN",
                    "weekly_change": ((candles_1d[-1]["close"] - candles_1d[0]["close"]) / candles_1d[0]["close"]) * 100,
                    "data_source": "hyperliquid"
                }
            return {"weekly_trend": "UNKNOWN", "weekly_change": 0.0, "data_source": "error"}
        except Exception as e:
            logger.error(f"❌ Failed to get weekly trend analysis: {e}")
            return {"weekly_trend": "UNKNOWN", "weekly_change": 0.0, "data_source": "error"}
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get current data update status"""
        return {
            "hyperliquid_connected": True,
            "websocket_connected": self.hyperliquid_websocket.is_connected(),
            "last_update": time.time()
        }
    
    def update_cached_websocket_price(self, price: float):
        """Update cached WebSocket price"""
        self._cached_websocket_price = price
        self._last_price_update = time.time()
    
    def get_hyperliquid_analysis(self, current_price: float = None) -> Dict[str, Any]:
        """Get comprehensive Hyperliquid market analysis"""
        try:
            if current_price is None:
                current_price = self.get_hyperliquid_price()
            
            if not current_price:
                return {"error": "Could not get current price"}
            
            # Get market data manager for comprehensive analysis
            from core.market_data_manager import get_global_market_data_manager
            market_data_manager = get_global_market_data_manager()
            
            # Get comprehensive market analysis (no duplicates)
            analysis = market_data_manager.get_hyperliquid_data(self, "BTC")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid analysis: {e}")
            return {"error": str(e)}
    
    def get_market_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get market data - CENTRAL HUB for all market data"""
        try:
            return self.hyperliquid_api.get_market_data(symbol)
        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            return {"error": str(e)}
    
    def get_orderbook(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get order book data from WebSocket (real-time)"""
        try:
            # Try to get real-time orderbook data from WebSocket first
            if self.hyperliquid_websocket:
                websocket_orderbook = self.hyperliquid_websocket.get_orderbook_data()
                if websocket_orderbook and "levels" in websocket_orderbook:
                    return websocket_orderbook
            
            # Fallback to REST API
            return self.hyperliquid_api.get_orderbook(symbol)
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook: {e}")
            return {"error": str(e)}
    
    def get_recent_trades(self, symbol: str = "BTC", limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades data"""
        try:
            return self.hyperliquid_api.get_recent_trades(symbol, limit)
        except Exception as e:
            logger.error(f"❌ Failed to get recent trades: {e}")
            return []
    
    def get_funding_rate(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get funding rate data"""
        try:
            return self.hyperliquid_api.get_funding_rate(symbol)
        except Exception as e:
            logger.error(f"❌ Failed to get funding rate: {e}")
            return {"error": str(e)}
    
    def get_binance_volume(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Get Binance real-time volume data"""
        try:
            if self.binance_api:
                return self.binance_api.get_real_time_volume()
            else:
                logger.warning("⚠️ Binance API not available for volume data")
                return {"error": "Binance API not available"}
        except Exception as e:
            logger.error(f"❌ Failed to get Binance volume: {e}")
            return {"error": str(e)}
    
    def get_historical_candles(self, symbol: str = "BTC", interval: str = "5m", limit: int = 20) -> List[Dict[str, Any]]:
        """Get historical candles with BaseDataManager caching - CENTRAL HUB for all candle data
        
        OPTIMIZED CACHING:
        - Single cache key per interval (not per limit)
        - Fetches maximum needed and slices for different requests
        - Automatically updates cache when it expires based on interval duration
        """
        try:
            # OPTIMIZED: Use single cache key per interval, not per limit
            # This ensures all requests for the same interval share the same cached data
            cache_key = f"candles_{symbol}_{interval}"
            cache_duration = self._interval_cache_duration.get(interval, self.cache_duration)
            
            # Define maximum fetch limits for each interval to cover all use cases
            # These limits cover both regular analysis AND extended S/R analysis
            max_fetch_limits = {
                "1m": 60,    # 1 hour of 1m candles
                "5m": 288,   # 24 hours of 5m candles (covers all S/R needs - was requesting 288 in S/R calc)
                "1h": 168,   # 1 week of 1h candles (covers extended S/R analysis)
                "1d": 45     # 45 days for context analysis
            }
            
            fetch_limit = max_fetch_limits.get(interval, limit)
            
            # Check if we have cached data that's still valid
            if self._is_cache_valid(cache_key, cache_duration):
                logger.debug(f"📊 Using cached {interval} candles for {symbol} (requested: {limit}, cached: {len(self.cache[cache_key])})")
                cached_candles = self.cache[cache_key]
                # Return slice of requested candles from the cached data
                return cached_candles[-limit:] if len(cached_candles) >= limit else cached_candles
            
            # Fetch fresh data from API
            logger.debug(f"🕯️ Fetching fresh {interval} candles for {symbol} (max_limit: {fetch_limit})")
            candles = self._fetch_historical_candles(symbol, interval, fetch_limit)
            
            if candles:
                # Cache the FULL dataset using BaseDataManager's method
                self._cache_data(cache_key, candles)
                logger.info(f"📊 Cached {len(candles)} {interval} candles for {symbol} - All requests will slice from this")
                # Return slice of requested candles
                return candles[-limit:] if len(candles) >= limit else candles
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get historical candles: {e}")
            return []
    
    def get_ongoing_candle(self, symbol: str = "BTC", interval: str = "5m") -> Optional[Dict[str, Any]]:
        """Get ongoing candle data with BaseDataManager caching"""
        try:
            # Use BaseDataManager's caching for ongoing candle
            cache_key = f"ongoing_{symbol}_{interval}"
            
            # Check cache first (1 minute cache for ongoing candle)
            if self._is_cache_valid(cache_key, cache_duration=60):
                return self.cache[cache_key]
            
            # Fetch from API
            ongoing_candle = self._fetch_ongoing_candle(symbol, interval)
            
            # Cache the result
            if ongoing_candle:
                self._cache_data(cache_key, ongoing_candle)
            
            return ongoing_candle
            
        except Exception as e:
            logger.error(f"❌ Failed to get ongoing candle: {e}")
            return None
    
    def invalidate_candle_cache(self, symbol: str = "BTC", interval: str = None):
        """Invalidate historical candle cache for specific interval or all intervals
        
        This should be called when:
        - A candle period completes (e.g., every 5 minutes for 5m candles)
        - A new candle starts
        - Market data needs to be refreshed immediately
        
        Args:
            symbol: Trading symbol (default: "BTC")
            interval: Specific interval to invalidate (e.g., "5m"), or None for all intervals
        """
        try:
            if interval:
                # Invalidate specific interval
                cache_key = f"candles_{symbol}_{interval}"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                    if cache_key in self.cache_timestamps:
                        del self.cache_timestamps[cache_key]
                    logger.debug(f"🗑️ Invalidated {interval} cache for {symbol}")
            else:
                # Invalidate all intervals
                keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"candles_{symbol}_")]
                for key in keys_to_remove:
                    del self.cache[key]
                    if key in self.cache_timestamps:
                        del self.cache_timestamps[key]
                logger.debug(f"🗑️ Invalidated all interval caches for {symbol}")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache: {e}")
    
    def get_all_market_data(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get ALL market data in one call - SINGLE SOURCE OF TRUTH"""
        try:
            # Get all market data components
            current_price = self.get_hyperliquid_price()
            candles_5m = self.get_historical_candles(symbol, "5m", 20)
            
            # Get real-time volume from WebSocket trades (current 5m candle)
            real_time_volume = 0.0
            if self.hyperliquid_websocket:
                real_time_volume = self.hyperliquid_websocket.get_current_5m_volume()
            
            # Fallback to candle data if no real-time trades
            if real_time_volume == 0.0:
                if not candles_5m or len(candles_5m) < 3:
                    raise ValueError("Insufficient candle data for volume calculation")
                
                # Calculate average volume per minute from recent 5m candles
                recent_volumes = [candle.get('volume', 0) for candle in candles_5m[-3:]]
                avg_5m_volume = sum(recent_volumes) / len(recent_volumes)
                volume_per_minute = avg_5m_volume / 5  # Convert 5m volume to per minute
            else:
                # Use real-time trades volume
                volume_per_minute = real_time_volume
            
            volume_per_second = volume_per_minute / 60
            
            # Calculate volume category using VolumeCalculator
            from core.analysis.real_time.volume_calculator import get_global_volume_calculator
            volume_spike_result = get_global_volume_calculator().detect_volume_spike_from_binance(volume_per_minute, [])
            
            # Validate volume category - no fallbacks
            volume_category = volume_spike_result.get('volume_category')
            if not volume_category:
                raise ValueError("Volume category calculation failed - NO FALLBACKS")
            
            # Create volume data
            data_source = "hyperliquid_trades" if real_time_volume > 0.0 else "hyperliquid_candles"
            volume_data = {
                "current_volume_btc": volume_per_minute,
                "current_volume_usd": volume_per_minute * current_price,
                "real_time_volume_btc": volume_per_minute,
                "real_time_volume_usd": volume_per_minute * current_price,
                "volume_per_minute": volume_per_minute,
                "volume_per_second": volume_per_second,
                "trade_count_per_minute": 0,  # Not available from candles
                "volume_spike_detected": volume_spike_result.get('volume_spike_detected', False),
                "volume_ratio": volume_spike_result.get('volume_ratio', 1.0),
                "volume_category": volume_category,
                "data_source": data_source,
                "timestamp": time.time()
            }
            
            # Get Binance global volume data
            binance_volume_data = self.get_binance_volume("BTCUSDT")
            
            market_data = {
                "current_price": current_price,
                "market_data": self.get_market_data(symbol),
                "orderbook": self.get_orderbook(symbol),
                "recent_trades": self.get_recent_trades(symbol, 50),
                "funding_rate": self.get_funding_rate(symbol),
                "volume_data": volume_data,
                "binance_volume_data": binance_volume_data,
                "candles": {
                    "1m": self.get_historical_candles(symbol, "1m", 20),
                    "5m": candles_5m,
                    "1h": self.get_historical_candles(symbol, "1h", 24),
                    "1d": self.get_historical_candles(symbol, "1d", 7)
                },
                "ongoing_candle": self.get_ongoing_candle(symbol, "5m"),
                "weekly_trend": self.get_weekly_trend_analysis(),
                "timestamp": time.time()
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get all market data: {e}")
            return {"error": str(e)}
    
    # Required abstract methods from BaseDataManager
    def _fetch_historical_candles(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch historical candles from Hyperliquid API"""
        return self.hyperliquid_api.get_historical_candles(symbol, interval, limit)
    
    def _fetch_ongoing_candle(self, symbol: str, interval: str) -> Optional[Dict[str, Any]]:
        """Fetch ongoing candle from Hyperliquid API"""
        return self.hyperliquid_api.get_ongoing_candle(symbol, interval)
    
    def _fetch_current_price(self, symbol: str) -> float:
        """Fetch current price from Hyperliquid API"""
        return self.hyperliquid_api.get_current_price(symbol) or 0.0