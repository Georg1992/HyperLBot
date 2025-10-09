#!/usr/bin/env python3
"""
Base Data Manager - Common functionality for all data management classes
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from loguru import logger

class BaseDataManager(ABC):
    """Base class for all data management implementations"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_duration = 300  # 5 minutes default
    
    def get_historical_candles(self, symbol: str = "BTC", interval: str = "5m", limit: int = 20) -> List[Dict[str, Any]]:
        """Get historical candles - common implementation"""
        try:
            cache_key = f"candles_{symbol}_{interval}_{limit}"
            
            # Check cache first
            if self._is_cache_valid(cache_key):
                logger.debug(f"📊 Using cached candles for {symbol} {interval}")
                return self.cache[cache_key]
            
            # Fetch from API
            candles = self._fetch_historical_candles(symbol, interval, limit)
            
            # Cache the result
            self._cache_data(cache_key, candles)
            
            logger.debug(f"📊 Fetched {len(candles)} candles for {symbol} {interval}")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to get historical candles: {e}")
            return []
    
    def get_ongoing_candle(self, symbol: str = "BTC", interval: str = "5m") -> Optional[Dict[str, Any]]:
        """Get current ongoing candle - common implementation"""
        try:
            cache_key = f"ongoing_{symbol}_{interval}"
            
            # Check cache first
            if self._is_cache_valid(cache_key, cache_duration=60):  # 1 minute cache for ongoing candle
                return self.cache[cache_key]
            
            # Fetch from API
            ongoing_candle = self._fetch_ongoing_candle(symbol, interval)
            
            # Cache the result
            self._cache_data(cache_key, ongoing_candle)
            
            return ongoing_candle
            
        except Exception as e:
            logger.error(f"❌ Failed to get ongoing candle: {e}")
            return None
    
    # get_current_price method removed - WebSocket is the only price source
    # Price data comes exclusively from HyperliquidWebSocket.get_current_price()
    
    def _is_cache_valid(self, key: str, cache_duration: Optional[int] = None) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache or key not in self.cache_timestamps:
            return False
        
        duration = cache_duration or self.cache_duration
        import time
        return time.time() - self.cache_timestamps[key] < duration
    
    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[key] = data
        import time
        self.cache_timestamps[key] = time.time()
    
    @abstractmethod
    def _fetch_historical_candles(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """Abstract method for fetching historical candles - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _fetch_ongoing_candle(self, symbol: str, interval: str) -> Optional[Dict[str, Any]]:
        """Abstract method for fetching ongoing candle - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _fetch_current_price(self, symbol: str) -> float:
        """Abstract method for fetching current price - must be implemented by subclasses"""
        pass
