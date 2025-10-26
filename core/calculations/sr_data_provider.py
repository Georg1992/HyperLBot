#!/usr/bin/env python3
"""
SRDataProvider - Handles data fetching, ATR calculation, and caching
Responsible for fetching multi-timeframe candle data and computing volatility metrics
"""

import time
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger


class SRDataProvider:
    """
    Data provider for Support/Resistance calculations
    
    Responsibilities:
    - Fetch multi-timeframe candle data
    - Calculate ATR for volatility reference
    - Handle caching and data validation
    - Provide clean data interface to other components
    """
    
    def __init__(self, symbol: str = "BTC"):
        """
        Initialize data provider
        
        Args:
            symbol: Trading symbol (default: "BTC")
        """
        self.symbol = symbol
        self._cache = {}
        self._last_fetch_time = {}
        
    def fetch_multi_timeframe_data(self, current_price: float) -> Tuple[Dict[str, List[Dict]], float]:
        """
        Fetch multi-timeframe candle data and calculate ATR
        
        Args:
            current_price: Current price for validation
            
        Returns:
            Tuple of (candles_data, atr_14)
            
        Raises:
            ValueError: If insufficient data is available
        """
        try:
            logger.debug(f"📊 Fetching multi-timeframe data for {self.symbol}")
            
            # Import here to avoid circular dependencies
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            
            # Fetch candles with aggressive lookback for better MTF analysis
            # Note: HyperliquidAPI supports 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M
            candles_5m = self._fetch_candles_with_validation(historical_service, "5m", 500, "5m")
            candles_15m = self._fetch_candles_with_validation(historical_service, "15m", 300, "15m")
            candles_1h = self._fetch_candles_with_validation(historical_service, "1h", 300, "1h")
            
            # Calculate ATR(14) for volatility reference
            atr_14 = self._calculate_atr(candles_5m, 14)
            logger.debug(f"📊 ATR(14): {atr_14:.2f}")
            
            return {
                "5m": candles_5m,
                "15m": candles_15m,
                "1h": candles_1h
            }, atr_14
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe data fetching failed: {e}")
            raise ValueError(f"Data fetching failed: {e}")
    
    def _fetch_candles_with_validation(self, historical_service, timeframe: str, 
                                      lookback: int, min_required: str) -> List[Dict]:
        """
        Fetch candles with validation and caching
        
        Args:
            historical_service: Historical data service instance
            timeframe: Timeframe to fetch
            lookback: Number of candles to fetch
            min_required: Minimum required timeframe for validation
            
        Returns:
            List of candle dictionaries
            
        Raises:
            ValueError: If insufficient data
        """
        try:
            # Check cache first using CentralizedCache
            cache_key = f"{self.symbol}_{timeframe}_{lookback}"
            from core.services.centralized_cache import get_global_centralized_cache
            cache = get_global_centralized_cache()
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"📊 Using cached {timeframe} data")
                return cached_data
            
            # Fetch fresh data
            candles = historical_service.get_historical_candles(self.symbol, timeframe, lookback)
            
            if not candles:
                raise ValueError(f"No {timeframe} candles available")
            
            # Validate minimum data requirements (more flexible)
            min_candles = {"5m": 50, "15m": 20, "1h": 20}
            if len(candles) < min_candles.get(timeframe, 20):
                raise ValueError(f"Insufficient {timeframe} candles: {len(candles)}")
            
            # Cache the data using CentralizedCache
            cache.set(cache_key, candles)
            self._last_fetch_time[timeframe] = time.time()
            
            logger.debug(f"📊 Fetched {len(candles)} {timeframe} candles")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch {timeframe} candles: {e}")
            raise ValueError(f"Failed to fetch {timeframe} candles: {e}")
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """
        Calculate Average True Range (ATR)
        
        Args:
            candles: List of candle dictionaries
            period: ATR period (default: 14)
            
        Returns:
            ATR value
        """
        try:
            if len(candles) < period:
                return 0.0
            
            true_ranges = []
            
            for i in range(1, len(candles)):
                prev_close = candles[i-1].get('close', 0)
                high = candles[i].get('high', 0)
                low = candles[i].get('low', 0)
                close = candles[i].get('close', 0)
                
                if prev_close > 0 and high > 0 and low > 0 and close > 0:
                    tr1 = high - low
                    tr2 = abs(high - prev_close)
                    tr3 = abs(low - prev_close)
                    true_range = max(tr1, tr2, tr3)
                    true_ranges.append(true_range)
            
            if len(true_ranges) < period:
                return 0.0
            
            # Calculate ATR using Wilder's smoothing
            atr = sum(true_ranges[:period]) / period
            
            for i in range(period, len(true_ranges)):
                atr = ((atr * (period - 1)) + true_ranges[i]) / period
            
            return atr
            
        except Exception as e:
            logger.error(f"❌ ATR calculation failed: {e}")
            return 0.0
    
    def get_cached_data(self, timeframe: str) -> Optional[List[Dict]]:
        """
        Get cached data for a specific timeframe
        
        Args:
            timeframe: Timeframe to retrieve
            
        Returns:
            Cached candle data or None
        """
        cache_key = f"{self.symbol}_{timeframe}_500"  # Default lookback
        from core.services.centralized_cache import get_global_centralized_cache
        cache = get_global_centralized_cache()
        cached_data = cache.get(cache_key)
        return cached_data
    
    def invalidate_cache(self, timeframe: Optional[str] = None):
        """
        Invalidate cache for specific timeframe or all timeframes
        
        Args:
            timeframe: Specific timeframe to invalidate, or None for all
        """
        if timeframe:
            # Invalidate specific timeframe
            keys_to_remove = [key for key in self._cache.keys() if f"_{timeframe}_" in key]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug(f"📊 Invalidated {timeframe} cache")
        else:
            # Invalidate all cache
            self._cache.clear()
            logger.debug("📊 Invalidated all cache")
    
    def get_data_status(self) -> Dict[str, Any]:
        """
        Get current data status and cache information
        
        Returns:
            Dictionary with data status information
        """
        return {
            "symbol": self.symbol,
            "cached_timeframes": list(set([key.split('_')[1] for key in self._cache.keys()])),
            "cache_size": len(self._cache),
            "last_fetch_times": self._last_fetch_time.copy()
        }
