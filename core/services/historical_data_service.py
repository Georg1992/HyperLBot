#!/usr/bin/env python3
"""
Historical Data Service
Centralized historical candle data fetching and management
Single Responsibility: Historical data source for all components
"""

import time
from typing import Dict, Any, List
from loguru import logger


class HistoricalDataService:
    """Centralized service for all historical candle data"""
    
    def __init__(self, cache=None, candle_storage=None):
        """
        Initialize Historical Data Service with dependency injection (DIP compliance)
        
        Args:
            cache: CentralizedCache instance (optional, falls back to global singleton)
            candle_storage: CandleStorage instance (optional, creates new if None)
        """
        # Dependency injection for cache (DIP compliance)
        # Fallback to global singleton for backward compatibility
        if cache is None:
            from core.services.centralized_cache import get_global_centralized_cache
            self._cache = get_global_centralized_cache()
        else:
            self._cache = cache
        
        # Dependency injection for candle storage (DIP compliance)
        if candle_storage is None:
            from core.services.candle_storage import CandleStorage
            from config.config import TradingConfig
            self._candle_storage = CandleStorage(symbol=TradingConfig.SYMBOL)
        else:
            self._candle_storage = candle_storage
        
        # Database should have 5 years of historical data
        # On bot startup: backfill missing candles from last stored candle to now
        try:
            candle_count = self._candle_storage.get_candle_count()
            
            if candle_count == 0:
                # Database is empty - initialize with 5 years of historical data
                logger.info("📥 Candle storage database is empty - initializing with 5 years of historical data...")
                self._candle_storage.initialize_with_historical_data(years=5.0)
                candle_count = self._candle_storage.get_candle_count()
                logger.info(f"✅ Candle storage initialized with {candle_count:,} candles")
            else:
                # Database has data - backfill missing candles from last candle to now
                logger.info(f"💾 Candle storage has {candle_count:,} candles - backfilling missing candles...")
                self._candle_storage.backfill_missing_candles()
                final_count = self._candle_storage.get_candle_count()
                logger.info(f"✅ Candle storage database ready with {final_count:,} candles")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize candle storage: {e}")
            # Database is REQUIRED - raise error instead of continuing
            raise ValueError(f"Candle storage database initialization failed - database is required: {e}")
        
        logger.info("📊 Historical Data Service initialized - Single source for all candle data")
    
    def _validate_candle_structure(self, candles: List[Dict]) -> None:
        """
        Validate candle structure at boundary - NO FALLBACKS
        
        All candles must have required fields: timestamp, open, high, low, close, volume
        All price values must be positive and valid (high >= low, high >= open/close, low <= open/close)
        
        Raises:
            ValueError: If any candle is missing required fields or has invalid data
        """
        if not candles:
            raise ValueError("Candle list is empty (NO FALLBACKS)")
        
        required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
        for i, candle in enumerate(candles):
            if not isinstance(candle, dict):
                raise ValueError(f"Candle at index {i} is not a dictionary (NO FALLBACKS)")
            
            # Check all required fields are present
            for field in required_fields:
                if field not in candle:
                    raise ValueError(f"Candle at index {i} missing required field '{field}' (NO FALLBACKS)")
            
            # Validate price values
            try:
                timestamp = float(candle["timestamp"])
                open_price = float(candle["open"])
                high_price = float(candle["high"])
                low_price = float(candle["low"])
                close_price = float(candle["close"])
                volume = float(candle["volume"])
            except (ValueError, TypeError) as e:
                raise ValueError(f"Candle at index {i} has invalid numeric values: {e} (NO FALLBACKS)")
            
            # Validate price relationships
            if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                raise ValueError(f"Candle at index {i} has non-positive prices (O:{open_price}, H:{high_price}, L:{low_price}, C:{close_price}) (NO FALLBACKS)")
            
            if high_price < low_price:
                raise ValueError(f"Candle at index {i} has high < low (H:{high_price}, L:{low_price}) (NO FALLBACKS)")
            
            if high_price < open_price or high_price < close_price:
                raise ValueError(f"Candle at index {i} has high < open/close (H:{high_price}, O:{open_price}, C:{close_price}) (NO FALLBACKS)")
            
            if low_price > open_price or low_price > close_price:
                raise ValueError(f"Candle at index {i} has low > open/close (L:{low_price}, O:{open_price}, C:{close_price}) (NO FALLBACKS)")
            
            if volume < 0:
                raise ValueError(f"Candle at index {i} has negative volume: {volume} (NO FALLBACKS)")
    
    def get_historical_candles(self, symbol: str, timeframe: str, count: int) -> List[Dict]:
        """
        Get historical candles - database is the ONLY source of truth
        For 5m: directly from database
        For other timeframes: aggregated from 5m candles in database
        
        All candles are validated at boundary - NO FALLBACKS
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            timeframe: Candle timeframe (e.g., "5m", "1h", "1d")
            count: Number of candles to fetch
            
        Returns:
            List of validated historical candles
            
        Raises:
            ValueError: If database is not available, insufficient data, or candle validation fails
        """
        try:
            # Check cache first using centralized system
            cache_key = f"historical_candles_{symbol}_{timeframe}_{count}"
            cached_data = self._cache.get(cache_key)
            if cached_data:
                # Validate cached candles (NO FALLBACKS - trust but verify)
                self._validate_candle_structure(cached_data)
                return cached_data
            
            # Database is the ONLY source - no API fallbacks
            if not self._candle_storage:
                raise ValueError(f"❌ Candle storage database not available - cannot fetch {timeframe} candles for {symbol}")
            
            from config.config import TradingConfig
            if symbol.upper() != TradingConfig.SYMBOL.upper():
                raise ValueError(f"❌ Database only supports {TradingConfig.SYMBOL} - cannot fetch {timeframe} candles for {symbol}")
            
            # For 5m candles, get directly from database
            if timeframe == "5m":
                candles = self._candle_storage.get_candles_by_count(count)
                if not candles or len(candles) < count:
                    raise ValueError(f"❌ Insufficient 5m candles in database: requested {count}, got {len(candles) if candles else 0}")
                
                # Validate candle structure at boundary (NO FALLBACKS)
                self._validate_candle_structure(candles)
                
                # Cache the result
                self._cache.set(cache_key, candles)
                return candles
            
            # For other timeframes, aggregate from 5m candles
            elif timeframe == "15m":
                # 15m = 3 * 5m candles
                candles_5m_count = count * 3
                candles_5m = self._candle_storage.get_candles_by_count(candles_5m_count)
                if not candles_5m or len(candles_5m) < candles_5m_count:
                    raise ValueError(f"❌ Insufficient 5m candles in database for 15m aggregation: requested {candles_5m_count}, got {len(candles_5m) if candles_5m else 0}")
                
                candles_15m = self._aggregate_5m_to_15m(candles_5m, count)
                logger.debug(f"💾 Aggregated {len(candles_15m)} 15m candles from {len(candles_5m)} 5m candles in database")
                # Cache the result
                self._cache.set(cache_key, candles_15m)
                return candles_15m
            
            elif timeframe == "1h":
                # 1h = 12 * 5m candles
                candles_5m_count = count * 12
                candles_5m = self._candle_storage.get_candles_by_count(candles_5m_count)
                if not candles_5m or len(candles_5m) < candles_5m_count:
                    raise ValueError(f"❌ Insufficient 5m candles in database for 1h aggregation: requested {candles_5m_count}, got {len(candles_5m) if candles_5m else 0}")
                
                candles_1h = self._aggregate_5m_to_1h(candles_5m, count)
                # Validate aggregated candles (NO FALLBACKS)
                self._validate_candle_structure(candles_1h)
                # Cache the result
                self._cache.set(cache_key, candles_1h)
                return candles_1h
            
            elif timeframe == "1d":
                # 1d = 288 * 5m candles (24 hours * 12 candles per hour)
                candles_5m_count = count * 288
                candles_5m = self._candle_storage.get_candles_by_count(candles_5m_count)
                if not candles_5m or len(candles_5m) < candles_5m_count:
                    raise ValueError(f"❌ Insufficient 5m candles in database for 1d aggregation: requested {candles_5m_count}, got {len(candles_5m) if candles_5m else 0}")
                
                candles_1d = self._aggregate_5m_to_1d(candles_5m, count)
                # Validate aggregated candles (NO FALLBACKS)
                self._validate_candle_structure(candles_1d)
                # Cache the result
                self._cache.set(cache_key, candles_1d)
                return candles_1d
            
            elif timeframe == "1m":
                # 1m candles not stored - cannot aggregate from 5m
                raise ValueError("❌ 1m candles not available from database - database only stores 5m candles")
            
            else:
                raise ValueError(f"❌ Unsupported timeframe: {timeframe} - database only supports 5m, 15m, 1h, 1d (aggregated from 5m)")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch {timeframe} candles for {symbol} from database: {e}")
            raise
    
    def get_1m_candles(self, symbol: str, count: int) -> List[Dict]:
        """
        Get 1-minute candles - NOT AVAILABLE from database
        Database only stores 5m candles, cannot aggregate to 1m
        """
        raise ValueError("❌ 1m candles not available from database - database only stores 5m candles")
    
    def get_last_closed_candle_timestamp(self, interval: str = "5m") -> float:
        """
        Public API: timestamp of the latest closed candle for the given interval.
        Used for deterministic unified_data timestamp; no private attribute access by callers.

        Args:
            interval: Candle interval. Only "5m" supported (database stores 5m candles).

        Returns:
            Timestamp (seconds) of the latest closed candle.

        Raises:
            ValueError: If interval is not "5m", or no candle data available (NO FALLBACKS).
        """
        if interval != "5m":
            raise ValueError(
                f"get_last_closed_candle_timestamp only supports interval '5m' (NO FALLBACKS): got {interval!r}"
            )
        ts = self._candle_storage.get_last_timestamp()
        if ts is None:
            raise ValueError("No candle timestamp available for deterministic unified_data (NO FALLBACKS)")
        return float(ts)

    def update_latest_candle(self) -> None:
        """
        Public API: update storage with the latest completed 5m candle.
        Callers must not use _candle_storage directly.
        """
        self._candle_storage.update_with_latest_candle()

    def get_5m_candles(self, symbol: str, count: int, use_storage: bool = True) -> List[Dict]:
        """
        Get 5-minute candles - database is the ONLY source
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            count: Number of candles to fetch
            use_storage: Ignored (always uses database) - kept for backward compatibility
            
        Returns:
            List of 5-minute candles from database
        """
        return self.get_historical_candles(symbol, "5m", count)
    
    def get_1h_candles(self, symbol: str, count: int) -> List[Dict]:
        """Get 1-hour candles - aggregated from 5m candles in database"""
        return self.get_historical_candles(symbol, "1h", count)
    
    def get_1d_candles(self, symbol: str, count: int) -> List[Dict]:
        """Get 1-day candles - aggregated from 5m candles in database"""
        return self.get_historical_candles(symbol, "1d", count)
    
    def invalidate_cache(self, symbol: str, timeframe: str):
        """Invalidate cache for specific symbol and timeframe"""
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"🗑️ Invalidated cache for {symbol} {timeframe}")
    
    def prepare_chart_data(self, current_price: float, pattern_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prepare complete chart data structure for dashboard
        
        Args:
            current_price: Current market price
            pattern_analysis: Pattern analysis data to include
            
        Returns:
            Dict with chart data structure
        """
        try:
            # Get the current 5m candle start time (UTC synchronized)
            candle_start_timestamp = self._get_5m_candle_start_time()
            
            # HistoricalDataService fetches its own candles (single responsibility)
            chart_candles_5m = self.get_5m_candles("BTC", 20)
            
            # NO FALLBACKS - Must have candles
            if not chart_candles_5m or len(chart_candles_5m) == 0:
                raise ValueError("NO CANDLES AVAILABLE - NO FALLBACKS: Database must be populated with historical candles")
            
            # Get real-time volume from the last candle if available
            # Candles are validated at boundary - volume is guaranteed (NO FALLBACKS)
            if not chart_candles_5m:
                raise ValueError("Chart candles list is empty (NO FALLBACKS)")
            real_time_volume = chart_candles_5m[-1]["volume"]
            
            # Determine which candles to display
            # We need exactly 19 completed candles + 1 ongoing = 20 total
            # Check if the last candle in database is the current ongoing candle or a completed one
            if len(chart_candles_5m) > 0:
                last_candle_timestamp = chart_candles_5m[-1]["timestamp"]
                current_time = time.time()
                
                # A candle is "ongoing" if its timestamp matches the current 5-minute candle start
                # AND it's less than 5 minutes old (not yet completed)
                candle_age = current_time - last_candle_timestamp
                is_ongoing_candle = (abs(last_candle_timestamp - candle_start_timestamp) < 10) and (candle_age < 300)
                
                if is_ongoing_candle:
                    # Last candle is the current ongoing one - remove it from historical, we'll create a fresh ongoing candle
                    chart_candles_5m = chart_candles_5m[:-1]
                else:
                    # Last candle is completed - keep only 19 to make room for ongoing candle (total 20)
                    if len(chart_candles_5m) > 19:
                        chart_candles_5m = chart_candles_5m[-19:]  # Keep only last 19 completed candles
            
            # Create ongoing candle using utility method
            ongoing_candle = self._create_ongoing_candle(
                current_price, chart_candles_5m, real_time_volume, candle_start_timestamp
            )
            
            # Map pattern indices from 50-candle detection array to 20-candle display array
            # Patterns are detected on 50 candles, but we display only 20 (last 20)
            # For pattern mapping, we need to include the ongoing candle in the array
            chart_candles_with_ongoing = chart_candles_5m.copy()
            chart_candles_with_ongoing.append(ongoing_candle)
            
            # IMPORTANT: Deep copy pattern_analysis to avoid mutating the cached object
            mapped_pattern_analysis = pattern_analysis
            if pattern_analysis and "patterns" in pattern_analysis and pattern_analysis["patterns"]:
                import copy
                pattern_analysis_copy = copy.deepcopy(pattern_analysis)
                mapped_pattern_analysis = self._map_pattern_indices_to_display_candles(
                    pattern_analysis_copy, chart_candles_with_ongoing
                )
            
            # Prepare chart data structure
            # IMPORTANT: historical should contain ONLY completed candles (19 candles)
            # ongoing should contain the current ongoing candle (1 candle)
            # Total: 20 candles for display
            return {
                "historical": chart_candles_5m,  # Only completed candles (19)
                "ongoing": ongoing_candle,  # Current ongoing candle (1)
                "predicted": [],
                "pattern_analysis": mapped_pattern_analysis or {}  # Pattern data with mapped indices
            }
            
        except Exception as e:
            logger.error(f"❌ Chart data preparation failed: {e}")
            raise
    
    def _map_pattern_indices_to_display_candles(self, patterns: Dict[str, Any], display_candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Map pattern indices from 50-candle detection array to 20-candle display array
        
        Patterns are detected on 50 candles (indices 0-49), but we display only 20 (last 20).
        This maps indices: pattern_index_in_50 → pattern_index_in_20
        Filters out patterns outside the visible 20-candle window.
        
        Args:
            patterns: Pattern analysis result with patterns array
            display_candles: The candles being displayed (20 candles)
            
        Returns:
            Patterns with mapped indices
        """
        try:
            if not patterns or ("patterns" not in patterns or not patterns["patterns"]):
                return patterns
            
            # Patterns are detected on 50 candles (indices 0-49, oldest to newest)
            # Display shows last 20 candles (indices 30-49 in 50-candle array = 0-19 in 20-candle array)
            DETECTION_CANDLE_COUNT = 50
            DISPLAY_CANDLE_COUNT = len(display_candles) if display_candles else 20
            
            # Calculate offset: patterns in range [offset, offset+DISPLAY_CANDLE_COUNT] are visible
            offset = DETECTION_CANDLE_COUNT - DISPLAY_CANDLE_COUNT
            
            # Process flat patterns array
            flat_patterns = patterns["patterns"] if "patterns" in patterns else []
            mapped_patterns = []
            
            for pattern in flat_patterns:
                start_idx = pattern["start_candle_index"] if "start_candle_index" in pattern else 0
                end_idx = pattern["end_candle_index"] if "end_candle_index" in pattern else start_idx
                
                # Check if pattern is visible in the display window
                # Pattern is visible if: end_idx is in visible range OR pattern spans the visible range
                pattern_visible = (
                    end_idx >= offset or  # Pattern ends in or after visible range
                    (start_idx < offset and end_idx >= offset)  # Pattern spans into visible range
                )
                
                if pattern_visible and end_idx < DETECTION_CANDLE_COUNT:
                    # Map indices: from 50-candle array to 20-candle array
                    # Clamp start_idx to visible range
                    mapped_start_idx = max(0, start_idx - offset)
                    mapped_end_idx = max(0, end_idx - offset)
                    
                    # Ensure indices are within display range
                    mapped_start_idx = max(0, min(mapped_start_idx, DISPLAY_CANDLE_COUNT - 1))
                    mapped_end_idx = max(0, min(mapped_end_idx, DISPLAY_CANDLE_COUNT - 1))
                    
                    # Create mapped pattern
                    mapped_pattern = pattern.copy()
                    mapped_pattern["start_candle_index"] = mapped_start_idx
                    mapped_pattern["end_candle_index"] = mapped_end_idx
                    mapped_patterns.append(mapped_pattern)
                else:
                    # Pattern is completely outside visible range, skip it
                    pattern_name = pattern["pattern"] if "pattern" in pattern else "unknown"
                    logger.debug(f"⏭️ Pattern {pattern_name} outside visible range (end_idx {end_idx} not >= {offset})")
            
            # Update patterns structure
            patterns["patterns"] = mapped_patterns
            
            # Also map nested patterns if they exist
            if "patterns_nested" in patterns and patterns["patterns_nested"]:
                nested = patterns["patterns_nested"]
                for category in ["reversal_patterns", "continuation_patterns", "triangle_patterns", 
                               "channel_patterns", "wedge_patterns", "candlestick_patterns", "trend_patterns"]:
                    if category in nested and nested[category]:
                        mapped_category = []
                        for pattern in nested[category]:
                            start_idx = pattern["start_candle_index"] if "start_candle_index" in pattern else 0
                            end_idx = pattern["end_candle_index"] if "end_candle_index" in pattern else start_idx
                            
                            # Check if pattern is visible (same logic as flat patterns)
                            pattern_visible = (
                                end_idx >= offset or
                                (start_idx < offset and end_idx >= offset)
                            )
                            
                            if pattern_visible and end_idx < DETECTION_CANDLE_COUNT:
                                mapped_pattern = pattern.copy()
                                mapped_pattern["start_candle_index"] = max(0, start_idx - offset)
                                mapped_pattern["end_candle_index"] = max(0, min(end_idx - offset, DISPLAY_CANDLE_COUNT - 1))
                                mapped_category.append(mapped_pattern)
                        nested[category] = mapped_category
                patterns["patterns_nested"] = nested
            
            logger.debug(f"📊 Mapped {len(mapped_patterns)} patterns from 50-candle array to {DISPLAY_CANDLE_COUNT}-candle display array")
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Failed to map pattern indices: {e}")
            return patterns
    
    def _aggregate_5m_to_15m(self, candles_5m: List[Dict], count: int) -> List[Dict]:
        """
        Aggregate 5-minute candles into 15-minute candles
        
        Args:
            candles_5m: List of 5-minute candles (oldest first)
            count: Number of 15-minute candles to create
            
        Returns:
            List of 15-minute candles
        """
        if not candles_5m or len(candles_5m) < 3:
            return []
        
        candles_15m = []
        # Group 3 consecutive 5m candles into 15m candles
        for i in range(0, min(len(candles_5m), count * 3), 3):
            group = candles_5m[i:i+3]
            if len(group) < 3:
                break
            
            # Aggregate OHLCV
            open_price = group[0]["open"]
            close_price = group[-1]["close"]
            high_price = max(c["high"] for c in group)
            low_price = min(c["low"] for c in group)
            total_volume = sum(c["volume"] for c in group)
            total_trades = sum(c["trades_count"] if "trades_count" in c else 0 for c in group)
            
            # Use timestamp of first 5m candle in the 15m period
            timestamp = group[0]["timestamp"]
            
            candles_15m.append({
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": total_volume,
                "timestamp": timestamp,
                "trades_count": total_trades
            })
        
        return candles_15m[-count:] if len(candles_15m) > count else candles_15m
    
    def _aggregate_5m_to_1h(self, candles_5m: List[Dict], count: int) -> List[Dict]:
        """
        Aggregate 5-minute candles into 1-hour candles
        
        Args:
            candles_5m: List of 5-minute candles (oldest first)
            count: Number of 1-hour candles to create
            
        Returns:
            List of 1-hour candles
        """
        if not candles_5m or len(candles_5m) < 12:
            return []
        
        candles_1h = []
        # Group 12 consecutive 5m candles into 1h candles
        for i in range(0, min(len(candles_5m), count * 12), 12):
            group = candles_5m[i:i+12]
            if len(group) < 12:
                break
            
            # Aggregate OHLCV
            open_price = group[0]["open"]
            close_price = group[-1]["close"]
            high_price = max(c["high"] for c in group)
            low_price = min(c["low"] for c in group)
            total_volume = sum(c["volume"] for c in group)
            total_trades = sum(c["trades_count"] if "trades_count" in c else 0 for c in group)
            
            # Use timestamp of first 5m candle in the hour
            timestamp = group[0]["timestamp"]
            
            candles_1h.append({
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": total_volume,
                "timestamp": timestamp,
                "trades_count": total_trades
            })
        
        return candles_1h[-count:] if len(candles_1h) > count else candles_1h
    
    def _aggregate_5m_to_1d(self, candles_5m: List[Dict], count: int) -> List[Dict]:
        """
        Aggregate 5-minute candles into 1-day candles
        
        Args:
            candles_5m: List of 5-minute candles (oldest first)
            count: Number of 1-day candles to create
            
        Returns:
            List of 1-day candles
        """
        if not candles_5m or len(candles_5m) < 288:
            return []
        
        candles_1d = []
        # Group 288 consecutive 5m candles into 1d candles (24 hours * 12 candles/hour)
        for i in range(0, min(len(candles_5m), count * 288), 288):
            group = candles_5m[i:i+288]
            if len(group) < 288:
                break
            
            # Aggregate OHLCV
            open_price = group[0]["open"]
            close_price = group[-1]["close"]
            high_price = max(c["high"] for c in group)
            low_price = min(c["low"] for c in group)
            total_volume = sum(c["volume"] for c in group)
            total_trades = sum(c["trades_count"] if "trades_count" in c else 0 for c in group)
            
            # Use timestamp of first 5m candle in the day (round to midnight)
            from datetime import datetime
            first_timestamp = group[0]["timestamp"]
            dt_obj = datetime.fromtimestamp(first_timestamp)
            # Round to midnight UTC
            midnight_dt = dt_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            timestamp = midnight_dt.timestamp()
            
            candles_1d.append({
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": total_volume,
                "timestamp": timestamp,
                "trades_count": total_trades
            })
        
        return candles_1d[-count:] if len(candles_1d) > count else candles_1d
    
    def _get_5m_candle_start_time(self) -> float:
        """
        Get the current 5-minute candle start time (UTC synchronized)
        
        Returns:
            Timestamp of current 5m candle start
        """
        from core.utils.time_utils import get_5m_candle_start_time
        return get_5m_candle_start_time()
    
    def _create_ongoing_candle(self, current_price: float, chart_candles_5m: List[Dict], 
                              real_time_volume: float, candle_start_timestamp: float) -> Dict[str, Any]:
        """
        Create ongoing candle structure with proper price movement
        
        Args:
            current_price: Current market price
            chart_candles_5m: Historical 5m candles for reference
            real_time_volume: Current 5m candle volume
            candle_start_timestamp: Timestamp of candle start
            
        Returns:
            Dict with ongoing candle data
        """
        current_time = time.time()
        
        # Get the open price from the last completed candle
        if chart_candles_5m and len(chart_candles_5m) > 0:
            open_price = chart_candles_5m[-1]["close"]  # Open of current candle = close of previous
        else:
            # Fallback: use current price as open (should not happen with proper data)
            open_price = current_price
        
        # Calculate proper high and low based on price movement
        high_price = max(open_price, current_price)
        low_price = min(open_price, current_price)
        
        # Ensure we have a proper candle structure
        if high_price == low_price:
            # If no price movement, create a small range to show the candle
            price_range = current_price * 0.0001  # 0.01% range
            high_price = current_price + price_range
            low_price = current_price - price_range
        
        return {
            "open": open_price,      # Price at start of 5m period
            "close": current_price,  # Current price as close
            "high": high_price,      # Highest price in current period
            "low": low_price,        # Lowest price in current period
            "volume": real_time_volume if real_time_volume > 0 else (chart_candles_5m[-1]["volume"] if chart_candles_5m else 0),
            "timestamp": candle_start_timestamp,
            "is_ongoing": True,
            "trades_count": 0,
            "last_trade_time": current_time
        }


# Factory function for dependency injection with singleton pattern
def create_historical_data_service(cache=None, candle_storage=None) -> HistoricalDataService:
    """
    Factory function to create HistoricalDataService with singleton pattern
    Prevents redundant initializations
    
    Args:
        cache: CentralizedCache instance (optional, falls back to global singleton)
        candle_storage: CandleStorage instance (optional, creates new if None)
    
    Returns:
        Configured HistoricalDataService instance (singleton)
    """
    global _global_historical_data_service
    if _global_historical_data_service is None:
        _global_historical_data_service = HistoricalDataService(cache=cache, candle_storage=candle_storage)
        logger.debug("📊 HistoricalDataService singleton created")
    return _global_historical_data_service

# Singleton pattern implementation for backward compatibility
_global_historical_data_service = None

def get_global_historical_data_service() -> HistoricalDataService:
    """Get the global HistoricalDataService singleton instance"""
    global _global_historical_data_service
    if _global_historical_data_service is None:
        _global_historical_data_service = create_historical_data_service()
    return _global_historical_data_service

