#!/usr/bin/env python3
"""
Enhanced Support/Resistance Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

import time
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from loguru import logger

# Import modular components
from .sr_data_provider import SRDataProvider
from .sr_detector import SRDetector
from .sr_scorer import SRScorer
from .sr_state import SRState
from .base_calculator import BaseCalculator
from .liquidation_calculator import LiquidationCalculator
from .level import Level

if TYPE_CHECKING:
    from core.services.centralized_cache import CentralizedCache


class SupportResistanceCalculator(BaseCalculator):
    """Enhanced Support/Resistance calculator with dynamic recalculation and MTF integration"""
    
    def __init__(self, symbol: str = "BTC", cache: Optional["CentralizedCache"] = None,
                 data_provider: Optional[SRDataProvider] = None, detector: Optional[SRDetector] = None, 
                 scorer: Optional[SRScorer] = None, state_manager: Optional[SRState] = None,
                 strategy: str = "standard"):
        """
        Initialize the refactored Support/Resistance Calculator
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_provider: SRDataProvider instance (injected dependency)
            detector: SRDetector instance (injected dependency)
            scorer: SRScorer instance (injected dependency)
            state_manager: SRState instance (injected dependency)
            strategy: Trading strategy name (default: "standard")
        """
        # Initialize base class with cache dependency
        super().__init__(symbol, cache)
        
        # Store strategy for level selection
        self._strategy = strategy
        
        # Dependency injection with defaults
        if data_provider is None:
            from core.services.historical_data_service import get_global_historical_data_service
            historical_service = get_global_historical_data_service()
            self._data_provider = SRDataProvider(symbol, historical_service, self._cache)
        else:
            self._data_provider = data_provider
            
        self._detector = detector or SRDetector()
        # Create scorer with strategy-specific configuration
        self._scorer = scorer or SRScorer(strategy=strategy)
        self._state = state_manager or SRState()
        self._liquidation_calc = LiquidationCalculator()
        
        # Performance optimization: Track module update times
        self._last_module_updates = {}
        self._min_recalculation_interval = 300  # 5 minutes minimum
        
        logger.info(f"📊 Refactored S/R Calculator initialized for {symbol} - Strategy: {strategy}")
    
    def _calculate_adaptive_tolerance(self, atr_14: float, current_price: float) -> float:
        """
        Calculate adaptive cluster tolerance using ATR (mathematically justified, NO FALLBACKS)
        
        Mathematical justification:
        - Base tolerance = 0.25 × ATR (25% of ATR for clustering)
        - This ensures tolerance scales with actual market volatility
        - ATR-based approach adapts to different volatility regimes
        
        Args:
            atr_14: 14-period ATR (required - must be positive)
            current_price: Current price (required - must be positive)
            
        Returns:
            Adaptive tolerance value in price units
            
        Raises:
            ValueError: If ATR or current_price is invalid
        """
        if atr_14 <= 0:
            raise ValueError(f"Invalid atr_14: {atr_14} - must be positive (NO FALLBACKS)")
        if current_price <= 0:
            raise ValueError(f"Invalid current_price: {current_price} - must be positive (NO FALLBACKS)")
        
        # Mathematically justified: 0.25 × ATR for clustering tolerance
        # This ensures levels within 25% of ATR are considered the same cluster
        atr_tolerance_multiplier = 0.25
        adaptive_tolerance = atr_14 * atr_tolerance_multiplier
        
        return adaptive_tolerance
    
    def _deduplicate_scored_levels(self, scored_levels: List, tolerance: float) -> List:
        """
        Final deduplication of scored levels to merge levels that are too close
        
        Args:
            scored_levels: List of scored Level objects
            tolerance: Distance tolerance for merging
            
        Returns:
            Deduplicated list of Level objects (merged by highest score)
        """
        try:
            if len(scored_levels) <= 1:
                return scored_levels
            
            # Sort by score (highest first) to keep best levels
            sorted_levels = sorted(scored_levels, key=lambda x: x.power or 0, reverse=True)
            deduplicated = []
            
            for level in sorted_levels:
                is_duplicate = False
                for existing in deduplicated:
                    if abs(level.level - existing.level) <= tolerance:
                        # Merge: keep the one with higher score (already sorted, so existing is better)
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    deduplicated.append(level)
            
            return deduplicated
            
        except Exception as e:
            logger.error(f"❌ Final deduplication failed: {e}")
            return scored_levels
    
    def _detect_all_swing_points(self, candles_data: Dict[str, List[Dict]], current_price: float) -> tuple:
        """
        Detect swing points for all timeframes - shared logic to avoid duplication
        
        Also detects daily/weekly/monthly peaks (absolute high/low of each period)
        
        Args:
            candles_data: Dictionary of candles by timeframe
            current_price: Current price
            
        Returns:
            Tuple of (swing_points_5m, higher_tf_levels)
        """
        swing_points_5m = self._detector.detect_swing_points(
            candles_data.get("5m", []), current_price, n=1, timeframe="5m")
        
        higher_tf_levels = []
        for tf in ["15m", "1h", "1d"]:
            tf_candles = candles_data.get(tf, [])
            if tf_candles:
                n_value = {"15m": 2, "1h": 3, "1d": 4}[tf]
                swing_tf = self._detector.detect_swing_points(tf_candles, current_price, n=n_value, timeframe=tf)
                higher_tf_levels.extend(swing_tf)
        
        # Detect daily/weekly/monthly peaks from 1d candles
        if candles_data.get("1d"):
            period_peaks = self._detect_period_peaks(candles_data.get("1d", []))
            higher_tf_levels.extend(period_peaks)
        
        return swing_points_5m, higher_tf_levels
    
    def _detect_period_peaks(self, daily_candles: List[Dict]) -> List[Level]:
        """
        Detect daily/weekly/monthly peaks (absolute high/low of each period)
        
        These are important S/R levels representing major price extremes:
        - Daily peaks: Highest/lowest price of each calendar day
        - Weekly peaks: Highest/lowest price of each calendar week
        - Monthly peaks: Highest/lowest price of each calendar month
        
        Args:
            daily_candles: List of 1-day candles
            
        Returns:
            List of Level objects representing period peaks
        """
        try:
            from datetime import datetime, timedelta
            
            if not daily_candles:
                return []
            
            period_peaks = []
            
            # Group candles by day/week/month
            daily_groups = {}
            weekly_groups = {}
            monthly_groups = {}
            
            for candle in daily_candles:
                timestamp = candle.get('timestamp', 0)
                if timestamp == 0:
                    continue
                
                dt = datetime.fromtimestamp(timestamp)
                
                # Group by day (YYYY-MM-DD)
                day_key = dt.strftime('%Y-%m-%d')
                if day_key not in daily_groups:
                    daily_groups[day_key] = []
                daily_groups[day_key].append(candle)
                
                # Group by week (YYYY-WW)
                # ISO week: Monday is day 1
                week_key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                if week_key not in weekly_groups:
                    weekly_groups[week_key] = []
                weekly_groups[week_key].append(candle)
                
                # Group by month (YYYY-MM)
                month_key = dt.strftime('%Y-%m')
                if month_key not in monthly_groups:
                    monthly_groups[month_key] = []
                monthly_groups[month_key].append(candle)
            
            # Find peaks for each period type
            # Daily peaks
            for day_key, day_candles in daily_groups.items():
                if day_candles:
                    day_high = max(c.get('high', 0) for c in day_candles)
                    day_low = min(c.get('low', 0) for c in day_candles)
                    day_timestamp = max(c.get('timestamp', 0) for c in day_candles)
                    
                    if day_high > 0:
                        period_peaks.append(Level(
                            level=day_high,
                            level_type='resistance',
                            touches=1,
                            cluster_size=1,
                            weighted_touches=1.0,
                            strength=80.0,  # Daily peaks are strong (major daily extremes)
                            timestamp=day_timestamp,
                            timeframe_distribution={'daily_peak': 1},
                            merged_from=1
                        ))
                    if day_low > 0:
                        period_peaks.append(Level(
                            level=day_low,
                            level_type='support',
                            touches=1,
                            cluster_size=1,
                            weighted_touches=1.0,
                            strength=80.0,  # Daily peaks are strong (major daily extremes)
                            timestamp=day_timestamp,
                            timeframe_distribution={'daily_peak': 1},
                            merged_from=1
                        ))
            
            # Weekly peaks
            for week_key, week_candles in weekly_groups.items():
                if week_candles:
                    week_high = max(c.get('high', 0) for c in week_candles)
                    week_low = min(c.get('low', 0) for c in week_candles)
                    week_timestamp = max(c.get('timestamp', 0) for c in week_candles)
                    
                    if week_high > 0:
                        period_peaks.append(Level(
                            level=week_high,
                            level_type='resistance',
                            touches=1,
                            cluster_size=1,
                            weighted_touches=1.0,
                            strength=90.0,  # Weekly peaks are very strong (major weekly extremes)
                            timestamp=week_timestamp,
                            timeframe_distribution={'weekly_peak': 1},
                            merged_from=1
                        ))
                    if week_low > 0:
                        period_peaks.append(Level(
                            level=week_low,
                            level_type='support',
                            touches=1,
                            cluster_size=1,
                            weighted_touches=1.0,
                            strength=90.0,  # Weekly peaks are very strong (major weekly extremes)
                            timestamp=week_timestamp,
                            timeframe_distribution={'weekly_peak': 1},
                            merged_from=1
                        ))
            
            # Monthly peaks
            for month_key, month_candles in monthly_groups.items():
                if month_candles:
                    month_high = max(c.get('high', 0) for c in month_candles)
                    month_low = min(c.get('low', 0) for c in month_candles)
                    month_timestamp = max(c.get('timestamp', 0) for c in month_candles)
                    
                    if month_high > 0:
                        period_peaks.append(Level(
                            level=month_high,
                            level_type='resistance',
                            touches=1,
                            cluster_size=1,
                            weighted_touches=1.0,
                            strength=100.0,  # Monthly peaks are maximum strength (major monthly extremes)
                            timestamp=month_timestamp,
                            timeframe_distribution={'monthly_peak': 1},
                            merged_from=1
                        ))
                    if month_low > 0:
                        period_peaks.append(Level(
                            level=month_low,
                            level_type='support',
                            touches=1,
                            cluster_size=1,
                            weighted_touches=1.0,
                            strength=100.0,  # Monthly peaks are maximum strength (major monthly extremes)
                            timestamp=month_timestamp,
                            timeframe_distribution={'monthly_peak': 1},
                            merged_from=1
                        ))
            
            logger.debug(f"📊 Detected {len(period_peaks)} period peaks (daily/weekly/monthly)")
            return period_peaks
            
        except Exception as e:
            logger.error(f"❌ Period peaks detection failed: {e}")
            return []
    
    def invalidate_cache(self):
        """Clear all cached S/R data to force fresh calculation"""
        self._cache.force_sr_recalculation()
        self._data_provider.invalidate_cache()
        logger.info("📊 S/R cache invalidated - next calculation will be fresh")
    
    def get_latest_analysis(self, current_price: float = None) -> Dict[str, Any]:
        """
        Get latest S/R analysis using the refactored modular system - NO FALLBACKS
        
        Args:
            current_price: Current price for analysis (required)
            
        Returns:
            S/R analysis dictionary
        
        Raises:
            ValueError: If current_price is None or calculation fails
        """
        try:
            if current_price is None:
                raise ValueError("Current price is required for S/R analysis - NO FALLBACKS")
            
            return self.calculate_multi_timeframe_levels(current_price)
                
        except Exception as e:
            logger.error(f"❌ Failed to get latest S/R analysis: {e}")
            raise
    
    def calculate_multi_timeframe_levels(self, current_price: float) -> Dict[str, Any]:
        """
        Clean S/R Algorithm: Find best support/resistance levels for trading
        
        STRATEGY INDEPENDENCE: Returns ALL significant levels without strategy-specific
        filtering. This ensures analysis is independent of trading strategy, which is
        determined AFTER analysis is complete.
        
        Algorithm:
        1. Start with 1 month of data (liquidation + time filtered)
        2. Process: swing detection → clustering → MTF → filtering → scoring
        3. If not enough levels, progressively expand time range (3m → 6m → 1y → 2y → 5y)
        4. Return ALL significant levels (prediction engine applies strategy filtering)
        
        Args:
            current_price: Current market price
        """
        # STRATEGY-INDEPENDENT MODE: Always use comprehensive parameters
        from core.calculations.sr_scorer import SRScorer
        if self._strategy != "comprehensive_analysis":
            self._scorer = SRScorer(strategy="comprehensive_analysis")
            self._strategy = "comprehensive_analysis"
        
        try:
            current_time = time.time()
            
            # Performance: Check cache first (strategy-independent)
            last_update = self._last_module_updates.get('support_resistance', 0)
            if current_time - last_update < self._min_recalculation_interval:
                cached_result = self._get_cached_analysis(current_price, current_time)
                if cached_result is not None and cached_result.get("status") == "ok":
                    return cached_result
            
            self._state.reset_session_state()
            
            # Calculate liquidation prices using actual Hyperliquid formula
            # Hyperliquid formula: liq_price = price - side * margin_available / position_size / (1 - l * side)
            # For S/R filtering, we use the maintenance margin rate directly (simplified for filtering purposes)
            # Actual rate observed: ~1.226% for 40x (not 2.5% theoretical)
            # This accounts for margin tiers and actual margin requirements
            long_liquidation = self._liquidation_calc.calculate_liquidation_price(current_price, "LONG")
            short_liquidation = self._liquidation_calc.calculate_liquidation_price(current_price, "SHORT")
            logger.debug(f"🔍 LIQUIDATION RANGE: LONG=${long_liquidation:.2f}, SHORT=${short_liquidation:.2f}, Current=${current_price:.2f}")
            
            # Progressive time expansion: Start with 1 month, expand if needed
            lookback_ranges = [
                (30, "1 month"),
                (90, "3 months"),
                (180, "6 months"),
                (365, "1 year"),
                (730, "2 years"),
                (1825, "5 years")
            ]
            
            scored_levels = []
            candles_data = {'5m': [], '15m': [], '1h': [], '1d': []}
            # Use data provider for all data access (separation of concerns)
            
            # Progressive expansion: Start with 1 month, expand if not enough levels
            for days, label in lookback_ranges:
                # Check if we have enough levels
                support_levels = [l for l in scored_levels if l.level_type == 'support' and l.level < current_price]
                resistance_levels = [l for l in scored_levels if l.level_type == 'resistance' and l.level > current_price]
                
                if len(support_levels) >= 2 and len(resistance_levels) >= 2:
                    logger.info(f"✅ Found sufficient levels: {len(support_levels)} support, {len(resistance_levels)} resistance")
                    break
                
                logger.debug(f"📊 Processing {label} of data (liquidation range filtered)...")
                
                # Fetch 5m candles for this time range (price + time filtered at database level)
                additional_5m_candles = self._data_provider._fetch_candles_in_liquidation_range(
                    current_price, long_liquidation, short_liquidation, days
                )
                
                if not additional_5m_candles:
                    logger.warning(f"⚠️ No candles found in liquidation range for {label}")
                    continue
                
                # Merge with existing 5m candles (avoid duplicates)
                existing_timestamps = {c.get('timestamp') for c in candles_data['5m']}
                new_5m_candles = [c for c in additional_5m_candles if c.get('timestamp') not in existing_timestamps]
                
                if new_5m_candles:
                    candles_data['5m'].extend(new_5m_candles)
                    candles_data['5m'].sort(key=lambda x: x.get('timestamp', 0))
                    logger.debug(f"🔍 Added {len(new_5m_candles)} 5m candles from {label} (total: {len(candles_data['5m'])})")
                
                # Fetch other timeframes for MTF alignment (no price filtering - just for swing detection)
                # Use data provider for all data access (separation of concerns)
                candles_data['15m'] = self._data_provider._fetch_candles_with_validation("15m", min(1000, days * 2))
                candles_data['1h'] = self._data_provider._fetch_candles_with_validation("1h", min(500, days))
                candles_data['1d'] = self._data_provider._fetch_candles_with_validation("1d", min(500, days))
                
                # Process candles → levels (single unified pipeline)
                processed_levels = self._process_candles_to_levels(
                    candles_data, current_price, current_time,
                    long_liquidation, short_liquidation
                )
                
                # Merge with existing levels (avoid duplicates by price)
                existing_prices = {l.level for l in scored_levels}
                new_levels = [l for l in processed_levels if l.level not in existing_prices]
                scored_levels.extend(new_levels)
                
                # Re-deduplicate and re-sort by power
                # Mathematically justified: Use 0.125 × ATR for final deduplication (tighter than clustering)
                atr_14 = self._data_provider.calculate_atr(candles_data.get('5m', []), 14)
                if atr_14 <= 0:
                    raise ValueError(f"Invalid atr_14: {atr_14} - must be positive for deduplication (NO FALLBACKS)")
                final_dedup_tolerance = atr_14 * 0.125  # 0.125×ATR for final deduplication
                scored_levels = self._deduplicate_scored_levels(scored_levels, final_dedup_tolerance)
                scored_levels.sort(key=lambda x: x.power or 0, reverse=True)
            
            # Format and return results (strategy-independent, returns ALL levels)
            result = self._format_results_optimized(scored_levels, current_price, 
                                                   self._data_provider.calculate_atr(candles_data.get('5m', []), 14), 
                                                   current_time)
            
            # Log final results
            all_levels = result.get('levels', [])
            active_support_count = len([l for l in all_levels if l.get("type") == "support" and l.get("status") == "active"])
            active_resistance_count = len([l for l in all_levels if l.get("type") == "resistance" and l.get("status") == "active"])
            logger.info(f"📊 FINAL: {len(all_levels)} total levels ({active_support_count} active support, {active_resistance_count} active resistance)")
            
            self._state.update_calculation_state(current_price, current_time)
            self._last_module_updates['support_resistance'] = current_time
            
            return result
            
        except Exception as e:
            logger.error(f"❌ S/R calculation failed: {e}")
            raise  # NO FALLBACKS - calculation failure should raise, not return error dict
    
    def _process_candles_to_levels(self, candles_data: Dict[str, List[Dict]], current_price: float,
                                   current_time: float, long_liquidation: float, short_liquidation: float) -> List:
        """
        Unified processing pipeline: candles → scored levels
        
        Single clean algorithm:
        1. Detect swing points
        2. Cluster with scoring (strength × proximity × recency)
        3. Search for additional touches (1-touch levels)
        4. MTF alignment
        5. Filter by liquidation range
        6. Filter by touch count (2+ or valid 1-touch)
        7. Score with historical reversal probability
        8. Deduplicate
        
        Returns: List of scored Level objects
        """
        try:
            # Calculate ATR for all timeframes
            atr_14 = self._data_provider.calculate_atr(candles_data.get('5m', []), 14)
            atr_per_tf = {
                '5m': atr_14,
                '15m': self._data_provider.calculate_atr(candles_data.get('15m', []), 14) if candles_data.get('15m') else atr_14 * 3,
                '1h': self._data_provider.calculate_atr(candles_data.get('1h', []), 14) if candles_data.get('1h') else atr_14 * 12,
                '1d': self._data_provider.calculate_atr(candles_data.get('1d', []), 14) if candles_data.get('1d') else atr_14 * 288
            }
            
            # 1. Detect swing points
            swing_points_5m, higher_tf_levels = self._detect_all_swing_points(candles_data, current_price)
            # Only log if significant number of swing points (reduce noise)
            if len(swing_points_5m) > 50:
                logger.debug(f"🔍 Detected {len(swing_points_5m)} swing points")
            
            # 2. Cluster with scoring (strength × proximity × recency)
            cluster_tolerance = self._calculate_adaptive_tolerance(atr_14, current_price)
            clustered_levels = self._detector.cluster_levels(
                swing_points_5m, cluster_tolerance, current_price, current_time, atr_14
            )
            
            # 3. Search for additional touches (1-touch levels)
            levels_with_1_touch = [l for l in clustered_levels if l.touches == 1]
            if levels_with_1_touch:
                clustered_levels = self._search_database_for_additional_touches(
                    clustered_levels, levels_with_1_touch, candles_data.get("5m", []), cluster_tolerance, atr_14
                )
            
            # 4. MTF alignment
            aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_per_tf)
            
            # 5. Filter by cluster size - only allow actual clusters (cluster_size >= 2)
            # Single isolated swing points are not valid S/R levels
            # Note: Liquidation filtering removed - natural filtering via score and strategy max_distance_pct
            scorable_levels = []
            for level in aligned_levels:
                # Only allow levels that are actual clusters (at least 2 swing points clustered together)
                # cluster_size >= 2 means multiple swing points were found at similar price levels
                if level.cluster_size >= 2:
                    scorable_levels.append(level)
                # Note: Single isolated swing points (cluster_size=1) are discarded
                # They need to cluster with other swing points to be valid S/R levels
            
            # 7. Calculate power (pure strength: touch, volume, reversal_probability)
            trend_data = self._get_trend_data()
            scored_levels = self._scorer.calculate_power(
                scorable_levels, current_price, atr_14, atr_per_tf,
                candles_data=candles_data, trend_data=trend_data
            )
            
            # 8. Deduplicate
            # Mathematically justified: Use 1.5 × ATR for final deduplication
            # Rationale:
            # - Clustering uses 0.25×ATR (tight, creates initial clusters)
            # - MTF alignment uses 0.5×ATR (looser, aligns across timeframes)
            # - Final deduplication uses 1.5×ATR (loosest, merges nearby clusters)
            # This ensures levels within ~1.5×ATR are merged (typically ~0.15% of price)
            # Example: At $90k with ATR=$90, tolerance=$135 merges levels ~0.15% apart
            if atr_14 <= 0:
                raise ValueError(f"Invalid atr_14: {atr_14} - must be positive for deduplication (NO FALLBACKS)")
            final_dedup_tolerance = atr_14 * 1.5  # 1.5×ATR for final deduplication (progressive: cluster 0.25×, MTF 0.5×, dedup 1.5×)
            scored_levels = self._deduplicate_scored_levels(scored_levels, final_dedup_tolerance)
            
            return scored_levels
            
        except Exception as e:
            logger.error(f"❌ Processing pipeline failed: {e}")
            return []
    
    def _get_trend_data(self) -> Dict[str, Any]:
        """Get trend data for probability adjustment - NO FALLBACKS"""
        try:
            from core.services.market_data_service import get_global_market_data_service
            market_service = get_global_market_data_service()
            if not market_service:
                raise ValueError("MarketDataService not available - NO FALLBACKS")
            
            trend_analysis = market_service.get_trend_analysis()
            if not trend_analysis or not isinstance(trend_analysis, dict):
                raise ValueError("Invalid trend analysis data - NO FALLBACKS")
            
            return {
                'direction': trend_analysis.get('direction', 'SIDEWAYS'),
                'strength': trend_analysis.get('strength', 0.0)
            }
        except Exception as e:
            logger.error(f"❌ Failed to get trend data: {e}")
            raise  # NO FALLBACKS - trend data is required for proper scoring
    
    def _get_cache_key(self, current_price: float, current_time: float) -> str:
        """
        Generate consistent cache key for S/R analysis (strategy-independent)
        
        Args:
            current_price: Current price
            current_time: Current timestamp
            
        Returns:
            Cache key string with price precision
        """
        timestamp_bucket = self._get_timestamp_bucket(current_time)
        # Use price with 2 decimal precision to avoid collisions
        price_key = f"{current_price:.2f}".replace('.', 'p')
        # Strategy-independent cache key
        return f"sr_analysis_{self.symbol}_5m_{timestamp_bucket}_{price_key}"
    
    def _get_timestamp_bucket(self, current_time: float) -> int:
        """
        Get 5-minute timestamp bucket for cache key consistency
        
        Args:
            current_time: Current timestamp
            
        Returns:
            5-minute timestamp bucket
        """
        return int(current_time // 300) * 300
    
    def _get_cached_analysis(self, current_price: float, current_time: float) -> Dict[str, Any]:
        """
        Get cached analysis if available (strategy-independent)
        
        Args:
            current_price: Current price
            current_time: Current timestamp
            
        Returns:
            Cached analysis or None if cache miss
        """
        try:
            # Create timestamp bucket (5-minute buckets) without strategy
            cache_key = self._get_cache_key(current_price, current_time)
            
            cached_data = self._cache.get(cache_key)
            if cached_data:
                return cached_data
            # No valid cache - this is normal, not an error (just means we need to calculate fresh)
            # Return None to indicate cache miss, not an error result
            return None
            
        except Exception as e:
            logger.error(f"❌ Cache retrieval failed: {e}")
            raise  # NO FALLBACKS - cache retrieval failure should raise, not return error dict
    
    def _search_database_for_additional_touches(self, clustered_levels: List, levels_with_1_touch: List, 
                                                current_candles: List[Dict], cluster_tolerance: float, 
                                                atr_14: float) -> List:
        """
        Search database for additional touches for levels with only 1 touch
        
        For levels that only have 1 touch in the current dataset, search the database
        further back to find additional swing points at similar price levels.
        We have 5 years of 5m candles in the database, so we can look back much further.
        
        Args:
            clustered_levels: All clustered levels
            levels_with_1_touch: Levels that only have 1 touch (need to search for more)
            current_candles: Current candles we've already analyzed
            cluster_tolerance: Tolerance for matching price levels
            atr_14: ATR for touch tolerance
            
        Returns:
            Updated list of clustered levels with additional touches found
        """
        try:
            if not levels_with_1_touch or not current_candles:
                return clustered_levels
            
            # Get the oldest timestamp from current candles to know where to start looking back
            oldest_timestamp = min(candle.get('timestamp', 0) for candle in current_candles)
            
            # Look back up to 2 years (we have 5 years of data)
            # 2 years = ~105,000 5m candles, but we'll fetch in chunks to avoid memory issues
            lookback_days = 730  # 2 years
            lookback_timestamp = oldest_timestamp - (lookback_days * 24 * 3600)
            
            # Fetch additional candles from database (older than what we already have)
            # Use data provider for all data access (separation of concerns)
            if self._data_provider._historical_service._candle_storage:
                additional_candles = self._data_provider._historical_service._candle_storage.get_candles_by_range(
                    lookback_timestamp, oldest_timestamp - 300  # Exclude the last 5 minutes to avoid overlap
                )
                
                if not additional_candles:
                    logger.debug(f"🔍 No additional candles found in database (looking back {lookback_days} days)")
                    return clustered_levels
                
                logger.debug(f"🔍 Found {len(additional_candles)} additional candles in database (looking back {lookback_days} days)")
                
                # Detect swing points in the additional historical data
                # Use a more sensitive swing detection to catch more potential touches
                additional_swing_points = self._detector.detect_swing_points(
                    additional_candles, 
                    current_price=0,  # Not needed for historical detection
                    n=1,  # More sensitive (n=1) to catch more swing points
                    timeframe="5m"
                )
                
                logger.debug(f"🔍 Found {len(additional_swing_points)} additional swing points in historical data")
                
                # For each level with only 1 touch, check if any additional swing points match
                updated_levels = []
                
                for level in clustered_levels:
                    if level in levels_with_1_touch:
                        # Check if any additional swing points are within cluster tolerance
                        matching_swings = []
                        for swing in additional_swing_points:
                            # Check if swing is same type and within tolerance
                            if swing.level_type == level.level_type:
                                price_diff = abs(swing.level - level.level)
                                if price_diff <= cluster_tolerance:
                                    matching_swings.append(swing)
                        
                        if matching_swings:
                            # Found additional touches! Update the level
                            total_touches = level.touches + len(matching_swings)
                            # Only log significant touch increases (5+ touches or doubling)
                            if total_touches >= 5 or total_touches >= level.touches * 2:
                                logger.debug(f"✅ Found {len(matching_swings)} additional touch(es) for {level.level_type} ${level.level:.2f} (now {total_touches}x touches)")
                            
                            # Create updated level with new touch count
                            updated_level = Level(
                                level=level.level,
                                level_type=level.level_type,
                                touches=total_touches,
                                cluster_size=level.cluster_size + len(matching_swings),
                                weighted_touches=level.weighted_touches + len(matching_swings),
                                strength=level.strength,  # Keep original strength
                                timestamp=max(level.timestamp, max(s.timestamp for s in matching_swings)),  # Latest touch
                                timeframe_distribution=level.timeframe_distribution,
                                mtf_matches=level.mtf_matches,
                                mtf_count=level.mtf_count,
                                mtf_confidence=level.mtf_confidence,
                                merged_from=level.merged_from,
                                power=level.power,
                                power_breakdown=level.power_breakdown
                            )
                            updated_levels.append(updated_level)
                        else:
                            # No additional touches found, keep original level
                            updated_levels.append(level)
                    else:
                        # Level already has 2+ touches, keep as is
                        updated_levels.append(level)
                
                return updated_levels
            else:
                logger.warning("⚠️ Candle storage not available - cannot search database for additional touches")
                return clustered_levels
                
        except Exception as e:
            logger.error(f"❌ Failed to search database for additional touches: {e}")
            return clustered_levels
    
    def _format_results_optimized(self, scored_levels: List, current_price: float, 
                                 atr_14: float, current_time: float) -> Dict[str, Any]:
        """
        Format results with optimized performance and proper state management
        
        Args:
            scored_levels: List of scored levels
            current_price: Current price
            atr_14: ATR for level status checking
            current_time: Current timestamp
            
        Returns:
            Formatted result dictionary (strategy-independent, returns ALL levels)
        """
        try:
            # Calculate ATR as percentage for level metadata
            atr_pct = atr_14 / current_price if current_price > 0 else 0.0
            
            # Process levels with state management
            key_levels = []
            active_count = 0
            inactive_count = 0
            mtf_confirmed_count = 0
            
            for level in scored_levels:
                # Check level status
                level_status = self._state.check_level_status(level, current_price, atr_14)
                
                # Track broken levels
                if level_status == 'inactive':
                    self._state.track_broken_level(level, current_price)
                    inactive_count += 1
                else:
                    active_count += 1
                
                # Count MTF confirmations
                if level.mtf_count > 0:
                    mtf_confirmed_count += 1
                
                # Use original level_type from swing detection (don't recalculate based on price position)
                # This preserves historical context: a broken resistance below price is still resistance
                key_levels.append({
                    "price_level": level.level,
                    "type": level.level_type,  # Use original level_type from swing detection
                    "strength_score": level.power,  # Use power (pure strength) for backward compatibility
                    "power": level.power,  # New field: pure level strength
                    "multi_tf": level.mtf_count > 0,
                    "status": level_status,
                    "touches": level.touches,
                    "weighted_touches": level.weighted_touches,  # Required for scoring
                    "cluster_size": level.cluster_size,  # Required for scoring
                    "last_touch_timestamp": level.timestamp,
                    "mtf_count": level.mtf_count,
                    "mtf_confidence": level.mtf_confidence,
                    "power_breakdown": level.power_breakdown or {},  # Power breakdown
                    "score_breakdown": level.power_breakdown or {},  # Backward compatibility alias
                    "merged_from": level.merged_from,
                    "atr_pct": atr_pct  # Required for distance-based scoring
                })
            
            # Sort by power (pure strength: touch, volume, reversal_probability)
            # Highest power wins - represents inherent level quality
            # Safely handle None values with explicit or chain
            key_levels.sort(key=lambda x: (x.get("power") or x.get("strength_score") or 0), reverse=True)
            
            # Calculate strongest support and resistance for metadata (use filter module)
            from .sr_level_filter import SRLevelFilter
            level_filter = SRLevelFilter(self.symbol)
            filtered_levels = level_filter.filter_for_display(
                all_levels=key_levels,
                current_price=current_price,
                max_levels=1  # Only need strongest (top 1), uses default "standard" weights
            )
            
            # Get strongest levels for metadata (highest score)
            strongest_support = filtered_levels["support"][0]["price_level"] if filtered_levels["support"] else 0.0
            support_score = filtered_levels["support"][0]["strength_score"] if filtered_levels["support"] else 0.0
            strongest_resistance = filtered_levels["resistance"][0]["price_level"] if filtered_levels["resistance"] else 0.0
            resistance_score = filtered_levels["resistance"][0]["strength_score"] if filtered_levels["resistance"] else 0.0
            
            # Get state summary for metadata
            state_summary = self._state.get_state_summary()
            
            result = {
                "status": "ok",
                "levels": key_levels,  # All swing-based S/R levels (modules filter as needed)
                "metadata": {
                    "timestamp": current_time,
                    "symbol": self.symbol,
                    "timeframe": "5m",
                    "atr_5m": atr_14,
                    "total_levels": len(scored_levels),
                    "filtered_levels": len(key_levels),
                    "active_levels": active_count,
                    "inactive_levels": inactive_count,
                    "mtf_confirmed": mtf_confirmed_count,
                    "broken_levels": state_summary['broken_levels_count'],
                    "role_reversals": state_summary['role_reversals_count'],
                    "recalculation_reasons": state_summary['recalculation_reasons'],
                    "strongest_support": strongest_support,
                    "strongest_resistance": strongest_resistance,
                    "support_score": support_score,
                    "resistance_score": resistance_score
                },
                # Root-level fields for dashboard compatibility (metadata only, not filtered levels)
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "support_score": support_score,
                "resistance_score": resistance_score,
                # Liquidation prices for trading at current price and S/R levels
                "liquidation_prices": self._liquidation_calc.calculate_liquidation_prices_for_levels(
                    strongest_support, strongest_resistance, current_price
                )
            }
            
            # Cache the result with strategy-independent key and TTL
            cache_key = self._get_cache_key(current_price, current_time)
            
            self._cache.set(cache_key, result, ttl=300)  # 5-minute TTL
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Result formatting failed: {e}")
            raise  # NO FALLBACKS - formatting failure should raise, not return error dict
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create error result with S/R-specific structure
        
        Args:
            error_message: Error message
            
        Returns:
            Error result dictionary
        """
        base_result = super()._create_error_result(error_message)
        return {
            **base_result,
            "levels": [],
            "metadata": {
                        "timestamp": time.time(),
                "symbol": self.symbol,
                "timeframe": "5m",
                "atr_5m": 0.0,
                "error": error_message,
                "total_levels": 0,
                "filtered_levels": 0,
                "active_levels": 0,
                "inactive_levels": 0,
                "mtf_confirmed": 0,
                "broken_levels": 0,
                "role_reversals": 0,
                "strongest_support": 0.0,
                "strongest_resistance": 0.0,
                "support_score": 0.0,
                "resistance_score": 0.0
            }
        }
    
    @staticmethod
    def select_stop_loss_level(
        levels: List[Dict[str, Any]],
        entry_price: float,
        direction: str,
        atr_5m: float,
        min_stop_distance: float,
        max_reasonable_distance: float = None,
        min_strength_score: float = 60.0
    ) -> Optional[Dict[str, Any]]:
        """
        Select the optimal S/R level for stop loss placement based on profitability considerations.
        
        Selection logic (prioritizes profitability):
        1. Prefer strong levels (strength_score >= min_strength_score) within max_reasonable_distance
        2. If no strong level within range, use closest level that meets minimum distance
        3. Ensures stop is not too tight (avoids false breaks) and not too wide (maintains R:R)
        
        Args:
            levels: List of S/R level dictionaries with keys: price_level, strength_score, status, type
            entry_price: Entry price
            direction: "LONG" or "SHORT"
            atr_5m: 5-minute ATR for distance calculations
            min_stop_distance: Minimum stop distance from entry (e.g., 2.0×ATR)
            max_reasonable_distance: Maximum reasonable distance (default: 3.0×ATR)
            min_strength_score: Minimum strength score to consider "strong" (default: 60.0)
            
        Returns:
            Selected level dictionary or None if no valid level found
        """
        if not levels:
            return None
        
        # Default max reasonable distance: 3×ATR (maintains reasonable R:R)
        if max_reasonable_distance is None:
            max_reasonable_distance = atr_5m * 3.0
        
        # Filter for active levels in the correct direction
        if direction == "LONG":
            # For LONG: need supports BELOW entry
            candidate_levels = [
                level for level in levels
                if level.get("type") == "support"
                and level.get("price_level", 0) < entry_price
                and level.get("status") == "active"
            ]
            # Calculate distance from entry (for LONG, distance = entry - level_price)
            def calc_distance(level):
                return entry_price - level.get("price_level", 0)
        else:  # SHORT
            # For SHORT: need resistances ABOVE entry
            candidate_levels = [
                level for level in levels
                if level.get("type") == "resistance"
                and level.get("price_level", 0) > entry_price
                and level.get("status") == "active"
            ]
            # Calculate distance from entry (for SHORT, distance = level_price - entry)
            def calc_distance(level):
                return level.get("price_level", 0) - entry_price
        
        if not candidate_levels:
            return None
        
        # Filter for levels that meet minimum distance requirement
        valid_levels = [
            level for level in candidate_levels
            if calc_distance(level) >= min_stop_distance
        ]
        
        if not valid_levels:
            return None
        
        # Strategy 1: Prefer strong levels within reasonable distance
        strong_levels_within_range = [
            level for level in valid_levels
            if level.get("strength_score", 0) >= min_strength_score
            and calc_distance(level) <= max_reasonable_distance
        ]
        
        if strong_levels_within_range:
            # Use strongest among those within reasonable distance
            selected = max(strong_levels_within_range, key=lambda x: x.get("strength_score", 0))
            logger.debug(f"✅ Selected strong {direction} stop level: ${selected.get('price_level', 0):.2f} (strength: {selected.get('strength_score', 0):.1f}, distance: {calc_distance(selected):.2f})")
            return selected
        
        # Strategy 2: No strong level within range - use closest that meets minimum
        # This maintains R:R while still providing protection
        selected = min(valid_levels, key=lambda x: calc_distance(x))
        logger.debug(f"✅ Selected closest {direction} stop level: ${selected.get('price_level', 0):.2f} (strength: {selected.get('strength_score', 0):.1f}, distance: {calc_distance(selected):.2f})")
        return selected


# Legacy singleton pattern removed - use dependency injection instead
# Create a factory function for backward compatibility
def create_sr_calculator(symbol: str = "BTC") -> SupportResistanceCalculator:
    """
    Factory function to create S/R calculator with dependency injection
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Configured SupportResistanceCalculator instance
    """
    return SupportResistanceCalculator(symbol=symbol)
    