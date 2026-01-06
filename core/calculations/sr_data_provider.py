#!/usr/bin/env python3
"""
SRDataProvider - Handles data fetching, ATR calculation, and caching
CHANGELOG: Added dependency injection, standardized ATR calculation with min fallback,
           improved error handling with graceful degradation for missing timeframes
"""

import time
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger


class SRDataProvider:
    """
    Data provider for Support/Resistance calculations with dependency injection
    
    Responsibilities:
    - Fetch multi-timeframe candle data
    - Calculate ATR for volatility reference
    - Handle caching and data validation
    - Provide clean data interface to other components
    """
    
    def __init__(self, symbol: str = "BTC", historical_service=None, cache=None, settings=None):
        """
        Initialize data provider with dependency injection
        
        Args:
            symbol: Trading symbol (default: "BTC")
            historical_service: Historical data service instance
            cache: Cache instance for data storage
            settings: Optional settings dictionary
        """
        self.symbol = symbol
        self.settings = settings or {}
        
        # Dependency injection with minimal factories
        if historical_service is None:
            from core.services.historical_data_service import create_historical_data_service
            self._historical_service = create_historical_data_service()
        else:
            self._historical_service = historical_service
            
        if cache is None:
            from core.services.centralized_cache import get_global_centralized_cache
            self._cache = get_global_centralized_cache()
        else:
            self._cache = cache
        
        self._last_fetch_time = {}
        
        # TTL mapping for different timeframes
        self._ttl_mapping = {
            "5m": 300,    # 5 minutes
            "15m": 900,   # 15 minutes
            "1h": 3600,   # 1 hour
            "1d": 86400   # 1 day
        }
        
    def fetch_multi_timeframe_data(self, current_price: float = None, force_extended_lookback: bool = False) -> Tuple[Dict[str, List[Dict]], Dict[str, float]]:
        """
        Fetch multi-timeframe candle data with progressive lookback
        Starts with minimal data and only increases if support (below) or resistance (above) is not found
        
        Args:
            current_price: Current price - used to determine if we need more historical data
            
        Returns:
            Tuple of (candles_data, atr_per_tf) where:
            - candles_data: Dictionary of candles by timeframe
            - atr_per_tf: Dictionary of ATR values per timeframe
            
        Raises:
            ValueError: If insufficient data is available for primary timeframe
        """
        try:
            # Start with sufficient lookback to find both support and resistance
            # Increased lookback to ensure we can count 2+ touches properly across historical data
            # For 2x touch requirement, we need enough history to see price revisit levels
            # We have 5 years of 5m candles in database (~525,600 candles), so we can look back much further
            # Fetch enough to find levels that were touched months ago (most levels get retested within 3-6 months)
            # 5m candles = 12/hour = 288/day = 8,640/month
            # 30,000 candles = ~104 days (~3.5 months) - should find 2nd touch for most recent levels
            candles_5m = self._fetch_candles_with_validation("5m", 30000)  # ~104 days (~3.5 months) - enough to find 2nd touch for recent levels
            candles_15m = self._fetch_candles_with_validation("15m", 1000)  # ~250 hours (~10 days) - increased for 2x touch detection
            candles_1h = self._fetch_candles_with_validation("1h", 500)   # ~21 days - increased for 2x touch detection
            candles_1d = self._fetch_candles_with_validation("1d", 500)   # ~500 days (~1.4 years) - increased to find levels with 2+ touches
            
            # Progressive lookback: Only increase if we can't find both support and resistance
            # Capped at 500 days (~1.5 years) - old levels (>1 year) are not actionable for short-term trading
            if current_price and current_price > 0:
                # Check if we have both support (below) and resistance (above) current price
                support_found = False
                resistance_found = False
                
                if candles_1d:
                    min_price = min(candle.get('low', float('inf')) for candle in candles_1d)
                    max_price = max(candle.get('high', 0) for candle in candles_1d)
                    
                    if min_price < current_price:
                        support_found = True
                    
                    if max_price > current_price:
                        resistance_found = True
                
                # Progressive lookback steps for daily candles if support or resistance not found
                # Need sufficient history to find resistance above month-high prices with 2+ touches
                lookback_steps = [750, 1000, 1500, 2000]  # Up to 2000 days (~5.5 years) to find levels with 2+ touches
                current_lookback = 2000 if force_extended_lookback else 500
                
                for step_lookback in lookback_steps:
                    if support_found and resistance_found:
                        break
                    
                    if step_lookback > current_lookback:
                        missing = []
                        if not support_found:
                            missing.append("support")
                        if not resistance_found:
                            missing.append("resistance")
                        
                        logger.warning(f"⚠️ Missing {', '.join(missing)} for ${current_price:.2f}, increasing daily lookback to {step_lookback} candles")
                        candles_1d = self._fetch_candles_with_validation("1d", step_lookback)
                        current_lookback = step_lookback
                        
                        if candles_1d:
                            min_price = min(candle.get('low', float('inf')) for candle in candles_1d)
                            max_price = max(candle.get('high', 0) for candle in candles_1d)
                            
                            if not support_found and min_price < current_price:
                                support_found = True
                            
                            if not resistance_found and max_price > current_price:
                                resistance_found = True
                
                if not support_found:
                    logger.warning(f"⚠️ Could not find support below ${current_price:.2f} even with {current_lookback} daily candles")
                if not resistance_found:
                    logger.warning(f"⚠️ Could not find resistance above ${current_price:.2f} even with {current_lookback} daily candles")
            
            # Calculate ATR for each timeframe
            atr_per_tf = {}
            for tf, candles in [("5m", candles_5m), ("15m", candles_15m), 
                               ("1h", candles_1h), ("1d", candles_1d)]:
                if candles:
                    atr_value = self.calculate_atr(candles, 14)
                    atr_per_tf[tf] = atr_value
                else:
                    atr_per_tf[tf] = 0.0
                    logger.warning(f"⚠️ No candles for {tf} timeframe")
            
            # Ensure all timeframes are returned (empty list if failed)
            candles_data = {
                "5m": candles_5m or [],
                "15m": candles_15m or [],
                "1h": candles_1h or [],
                "1d": candles_1d or []
            }
            
            return candles_data, atr_per_tf
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe data fetching failed: {e}")
            raise ValueError(f"Data fetching failed: {e}")
    
    def _fetch_candles_with_validation(self, timeframe: str, lookback: int) -> List[Dict]:
        """
        Fetch candles with validation and caching using injected dependencies
        
        Args:
            timeframe: Timeframe to fetch
            lookback: Number of candles to fetch
            
        Returns:
            List of candle dictionaries (empty list if insufficient data)
        """
        try:
            # Check cache first using injected cache with proper key structure
            timestamp_bucket = int(time.time() // 300) * 300  # 5-minute buckets
            cache_key = f"sr_candles_{self.symbol}_{timeframe}_{lookback}_{timestamp_bucket}"
            cached_data = self._cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Fetch fresh data using injected historical service
            candles = self._historical_service.get_historical_candles(self.symbol, timeframe, lookback)
            
            if not candles:
                logger.warning(f"⚠️ No {timeframe} candles available")
                return []
            
            # Validate minimum data requirements (graceful handling)
            min_candles = {"5m": 50, "15m": 20, "1h": 20, "1d": 10}
            if len(candles) < min_candles.get(timeframe, 20):
                logger.warning(f"⚠️ Insufficient {timeframe} candles: {len(candles)} (min: {min_candles.get(timeframe, 20)})")
                # Return empty list instead of raising error for graceful degradation
                return []
            
            # Cache the data using injected cache with TTL
            ttl = self._ttl_mapping.get(timeframe, 300)
            self._cache.set(cache_key, candles, ttl)
            self._last_fetch_time[timeframe] = time.time()
            
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch {timeframe} candles: {e}")
            return []  # Return empty list for graceful degradation
    
    def calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """
        Calculate Average True Range (ATR) with minimum fallback
        
        Args:
            candles: List of candle dictionaries
            period: ATR period (default: 14)
            
        Returns:
            ATR value (never returns zero - uses minimum fallback)
        """
        try:
            if len(candles) < period:
                # Return minimum ATR based on price
                if candles:
                    price = candles[-1].get('close', 100.0)
                    min_atr = max(price * 0.0005, 0.1)  # 0.05% of price or 0.1 minimum
                    logger.warning(f"⚠️ Insufficient candles for ATR, using min fallback: {min_atr:.2f}")
                    return min_atr
                else:
                    return 0.1  # Absolute minimum
            
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
                # Return minimum ATR based on price
                price = candles[-1].get('close', 100.0)
                min_atr = max(price * 0.0005, 0.1)
                logger.warning(f"⚠️ Insufficient true ranges for ATR, using min fallback: {min_atr:.2f}")
                return min_atr
            
            # Calculate ATR using Wilder's smoothing
            atr = sum(true_ranges[:period]) / period
            
            for i in range(period, len(true_ranges)):
                atr = ((atr * (period - 1)) + true_ranges[i]) / period
            
            # Ensure minimum ATR
            price = candles[-1].get('close', 100.0)
            min_atr = max(price * 0.0005, 0.1)
            final_atr = max(atr, min_atr)
            
            return final_atr
            
        except Exception as e:
            logger.error(f"❌ ATR calculation failed: {e}")
            # Return minimum ATR as fallback
            return 0.1
    
    def get_cached_data(self, timeframe: str) -> Optional[List[Dict]]:
        """
        Get cached data for a specific timeframe
        
        Args:
            timeframe: Timeframe to retrieve
            
        Returns:
            Cached candle data or None
        """
        cache_key = f"{self.symbol}_{timeframe}_500"  # Default lookback
        cached_data = self._cache.get(cache_key)
        return cached_data
    
    def invalidate_cache(self, timeframe: Optional[str] = None):
        """
        Invalidate cache for specific timeframe or all timeframes
        
        Args:
            timeframe: Specific timeframe to invalidate, or None for all
        """
        if timeframe:
            # Invalidate specific timeframe - use cache invalidate method
            pattern = f".*sr_candles_{self.symbol}_{timeframe}.*"
            self._cache.invalidate(pattern)
            logger.debug(f"📊 Invalidated {timeframe} cache")
        else:
            # Invalidate all cache - use cache invalidate method
            pattern = f".*sr_candles_{self.symbol}.*"
            self._cache.invalidate(pattern)
            logger.debug(f"📊 Invalidated all S/R cache for {self.symbol}")
    
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
