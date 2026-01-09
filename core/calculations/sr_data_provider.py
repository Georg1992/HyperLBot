#!/usr/bin/env python3
"""
SRDataProvider - Handles data fetching, ATR calculation, and caching
CHANGELOG: Added dependency injection, standardized ATR calculation with minimum safety value,
           improved error handling (NO FALLBACKS policy)
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
    
    def fetch_candles_by_price_range(self, min_price: float, max_price: float, 
                                     max_candles: int = 50000,
                                     min_timestamp: float = None) -> List[Dict[str, Any]]:
        """
        Smart query: Fetch candles that have lows/highs within a price range AND time range
        This is much more efficient than fetching all candles and filtering
        
        Args:
            min_price: Minimum price (e.g., liquidation price for support)
            max_price: Maximum price (e.g., current price for support)
            max_candles: Maximum number of candles to return
            min_timestamp: Optional minimum timestamp (seconds) - only return candles after this time
            
        Returns:
            List of candles where:
            - low <= max_price AND high >= min_price (price range overlap)
            - timestamp >= min_timestamp (if provided)
        """
        try:
            # Access candle storage directly for smart price + time range query
            if hasattr(self._historical_service, '_candle_storage') and self._historical_service._candle_storage:
                candles = self._historical_service._candle_storage.get_candles_by_price_range(
                    min_price, max_price, max_candles, min_timestamp
                )
                # Log only if significant number of candles found (reduce noise)
                if len(candles) > 1000:
                    if min_timestamp is not None:
                        logger.debug(f"🔍 Smart query (price + time): Found {len(candles)} candles in range ${min_price:.2f}-${max_price:.2f}")
                    else:
                        logger.debug(f"🔍 Smart price range query: Found {len(candles)} candles in range ${min_price:.2f}-${max_price:.2f}")
                return candles
            else:
                logger.warning("⚠️ Candle storage not available for price range query")
                return []
        except Exception as e:
            logger.error(f"❌ Price range query failed: {e}")
            return []
    
    def fetch_multi_timeframe_data(self, current_price: float = None, 
                                   long_liquidation: float = None,
                                   short_liquidation: float = None) -> Tuple[Dict[str, List[Dict]], Dict[str, float]]:
        """
        Fetch multi-timeframe candle data using smart price range queries within liquidation range
        
        Progressive lookback strategy:
        1. Start with 1 month of data (most recent swing points)
        2. Filter by liquidation range from the start (only fetch relevant candles)
        3. If not enough swing points, expand time range progressively
        4. Up to 5 years if needed (rarely - only for extreme price ranges)
        
        Args:
            current_price: Current price (required for liquidation range queries)
            long_liquidation: LONG liquidation price (for support level filtering)
            short_liquidation: SHORT liquidation price (for resistance level filtering)
            
        Returns:
            Tuple of (candles_data, atr_per_tf) where:
            - candles_data: Dictionary of candles by timeframe
            - atr_per_tf: Dictionary of ATR values per timeframe
            
        Raises:
            ValueError: If insufficient data is available for primary timeframe
        """
        try:
            if not current_price or current_price <= 0:
                raise ValueError("Current price is required for S/R calculation - NO FALLBACKS")
            
            # Calculate liquidation prices if not provided
            if long_liquidation is None or short_liquidation is None:
                try:
                    from core.calculations.liquidation_calculator import LiquidationCalculator
                    liquidation_calc = LiquidationCalculator()
                    if long_liquidation is None:
                        long_liquidation = liquidation_calc.calculate_liquidation_price(current_price, "LONG")
                    if short_liquidation is None:
                        short_liquidation = liquidation_calc.calculate_liquidation_price(current_price, "SHORT")
                except Exception as e:
                    logger.error(f"❌ Could not calculate liquidation prices: {e}")
                    # NO FALLBACKS - Liquidation prices are required for proper S/R filtering
                    raise ValueError(f"Liquidation price calculation failed - NO FALLBACKS: {e}")
            
            logger.debug(f"🔍 LIQUIDATION RANGE: LONG=${long_liquidation:.2f}, SHORT=${short_liquidation:.2f}, Current=${current_price:.2f}")
            
            # Start with 1 month - fetch only candles within liquidation range
            # Progressive expansion happens in calculator if not enough swing points
            candles_5m = self._fetch_candles_in_liquidation_range(
                current_price, long_liquidation, short_liquidation, days=30
            )
            
            if candles_5m:
                logger.info(f"✅ Found {len(candles_5m)} 5m candles within liquidation range for 1 month")
            else:
                # NO FALLBACKS - If no candles found in liquidation range, this is a data issue
                logger.warning(f"⚠️ No candles found in liquidation range for 1 month - price may be at extreme range")
                # Don't fetch without price filtering - let the calculator handle progressive expansion
            
            # For other timeframes, fetch reasonable amounts (they're used for MTF confirmation)
            # These don't need price filtering - they're just for higher timeframe swing detection
            candles_15m = self._fetch_candles_with_validation("15m", 480)  # 1 month
            candles_1h = self._fetch_candles_with_validation("1h", 720)  # 1 month
            candles_1d = self._fetch_candles_with_validation("1d", 30)  # 1 month
            
            # Calculate ATR for each timeframe
            atr_per_tf = self._calculate_atr_for_all_timeframes({
                "5m": candles_5m, "15m": candles_15m, "1h": candles_1h, "1d": candles_1d
            })
            
            # Return candles data
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
    
    def _fetch_candles_in_liquidation_range(self, current_price: float, long_liquidation: float,
                                           short_liquidation: float, days: int) -> List[Dict]:
        """
        Fetch candles for swing detection with expanded price range, then filter levels by liquidation
        
        Strategy:
        - Fetch candles in EXPANDED range (2% beyond liquidation) to catch all swing points
        - Swing detection will find all relevant levels
        - Final levels are filtered by liquidation range (safe for trading)
        
        This ensures we don't miss important swing points just outside liquidation range.
        
        Args:
            current_price: Current price
            long_liquidation: LONG liquidation price
            short_liquidation: SHORT liquidation price
            days: Number of days to look back
            
        Returns:
            List of candles in expanded range (for swing detection)
        """
        try:
            # Calculate time cutoff timestamp
            current_time = time.time()
            cutoff_timestamp = current_time - (days * 24 * 3600)
            
            # EXPAND price ranges by 2% to catch swing points just outside liquidation range
            # We'll filter the final levels by liquidation range, but need all swing points for detection
            expansion_factor = 0.02  # 2% expansion
            
            # Support: Expand below liquidation to catch swing points
            support_min_price = long_liquidation * (1 - expansion_factor)  # 2% below liquidation
            support_max_price = current_price
            
            # Resistance: Expand above short liquidation to catch swing points
            resistance_min_price = current_price
            resistance_max_price = short_liquidation * (1 + expansion_factor)  # 2% above short liquidation
            
            # Smart query: Fetch support candles (expanded range below current price)
            # WITH time filtering at database level
            support_candles = self.fetch_candles_by_price_range(
                support_min_price, support_max_price, 
                max_candles=50000, 
                min_timestamp=cutoff_timestamp  # Database filters by time!
            )
            
            # Smart query: Fetch resistance candles (expanded range above current price)
            # WITH time filtering at database level
            resistance_candles = self.fetch_candles_by_price_range(
                resistance_min_price, resistance_max_price, 
                max_candles=50000, 
                min_timestamp=cutoff_timestamp  # Database filters by time!
            )
            
            # Combine and deduplicate by timestamp (should already be deduplicated, but just in case)
            all_candles = {}
            for candle in support_candles + resistance_candles:
                ts = candle.get('timestamp', 0)
                if ts not in all_candles:
                    all_candles[ts] = candle
            
            # Convert to list and sort by timestamp (oldest first)
            filtered_candles = sorted(all_candles.values(), key=lambda x: x.get('timestamp', 0))
            
            # Only log if significant number found (reduce noise)
            if len(filtered_candles) > 100:
                logger.debug(f"🔍 Smart query: Found {len(filtered_candles)} candles in liquidation range for {days} days")
            
            return filtered_candles
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch candles in liquidation range: {e}")
            return []
    
    def _calculate_atr_for_all_timeframes(self, candles_data: Dict[str, List[Dict]]) -> Dict[str, float]:
        """Calculate ATR for all timeframes"""
        atr_per_tf = {}
        for tf, candles in candles_data.items():
            if candles:
                atr_value = self.calculate_atr(candles, 14)
                atr_per_tf[tf] = atr_value
            else:
                atr_per_tf[tf] = 0.0
                logger.warning(f"⚠️ No candles for {tf} timeframe")
        return atr_per_tf
    
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
            ATR value (never returns zero - uses minimum safety value to prevent division by zero)
        """
        try:
            if len(candles) < period:
                # Return minimum ATR based on price
                if candles:
                    price = candles[-1].get('close', 100.0)
                    min_atr = max(price * 0.0005, 0.1)  # 0.05% of price or 0.1 minimum
                    logger.warning(f"⚠️ Insufficient candles for ATR, using minimum safety value: {min_atr:.2f}")
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
                logger.warning(f"⚠️ Insufficient true ranges for ATR, using minimum safety value: {min_atr:.2f}")
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
            # NO FALLBACKS - Raise error instead of returning default value
            raise ValueError(f"ATR calculation failed - NO FALLBACKS: {e}")
    
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
