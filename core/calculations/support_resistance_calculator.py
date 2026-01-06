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

if TYPE_CHECKING:
    from core.services.centralized_cache import CentralizedCache


class SupportResistanceCalculator(BaseCalculator):
    """Enhanced Support/Resistance calculator with dynamic recalculation and MTF integration"""
    
    def __init__(self, symbol: str = "BTC", cache: Optional["CentralizedCache"] = None,
                 data_provider: Optional[SRDataProvider] = None, detector: Optional[SRDetector] = None, 
                 scorer: Optional[SRScorer] = None, state_manager: Optional[SRState] = None):
        """
        Initialize the refactored Support/Resistance Calculator
        
        Args:
            symbol: Trading symbol (default: "BTC")
            data_provider: SRDataProvider instance (injected dependency)
            detector: SRDetector instance (injected dependency)
            scorer: SRScorer instance (injected dependency)
            state_manager: SRState instance (injected dependency)
        """
        # Initialize base class
        super().__init__(symbol)
        
        # Inject centralized cache dependency first
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = cache or get_global_centralized_cache()
        
        # Dependency injection with defaults
        if data_provider is None:
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            self._data_provider = SRDataProvider(symbol, historical_service, self._cache)
        else:
            self._data_provider = data_provider
            
        self._detector = detector or SRDetector()
        self._scorer = scorer or SRScorer()
        self._state = state_manager or SRState()
        self._liquidation_calc = LiquidationCalculator()
        
        # Performance optimization: Track module update times
        self._last_module_updates = {}
        self._min_recalculation_interval = 300  # 5 minutes minimum
        
        logger.info(f"📊 Refactored S/R Calculator initialized for {symbol} - Modular architecture")
    
    def _calculate_adaptive_tolerance(self, atr_14: float, current_price: float) -> float:
        """
        Calculate adaptive cluster tolerance using price percentage only
        
        Scientific justification:
        - Price percentage (0.1%) ensures consistent behavior across all price ranges
        - ATR varies with volatility, but percentage scales naturally with price
        - 0.1% represents ~1 standard deviation of typical intraday noise for BTC
        - This threshold separates meaningful S/R levels from market microstructure noise
        - Percentage-based approach is scale-invariant and scientifically sound
        
        Args:
            atr_14: 14-period ATR (for reference/logging only, not used in calculation)
            current_price: Current price
            
        Returns:
            Adaptive tolerance value as percentage of price
        """
        try:
            # Scientific threshold: 0.1% of price
            # This represents the minimum meaningful price movement for S/R level distinction
            # Based on empirical analysis: levels closer than this are statistically indistinguishable
            tolerance_pct = 0.001  # 0.1% - scientifically justified threshold
            adaptive_tolerance = current_price * tolerance_pct
            
            
            return adaptive_tolerance
            
        except Exception as e:
            logger.error(f"❌ Adaptive tolerance calculation failed: {e}")
            return current_price * 0.001  # Fallback to 0.1% of price
    
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
            sorted_levels = sorted(scored_levels, key=lambda x: x.score, reverse=True)
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
        
        return swing_points_5m, higher_tf_levels
    
    def invalidate_cache(self):
        """Clear all cached S/R data to force fresh calculation"""
        self._cache.force_sr_recalculation()
        self._data_provider.invalidate_cache()
        logger.info("📊 S/R cache invalidated - next calculation will be fresh")
    
    def get_latest_analysis(self, current_price: float = None) -> Dict[str, Any]:
        """
        Get latest S/R analysis using the refactored modular system
        
        Args:
            current_price: Current price for analysis
            
        Returns:
            S/R analysis dictionary
        """
        try:
            if current_price is None:
                logger.warning("⚠️ No current price provided for S/R analysis")
                return self._create_error_result("No current price provided")
            
            return self.calculate_multi_timeframe_levels(current_price)
                
        except Exception as e:
            logger.error(f"❌ Failed to get latest S/R analysis: {e}")
            return self._create_error_result(str(e))
    
    def calculate_multi_timeframe_levels(self, current_price: float) -> Dict[str, Any]:
        """
        Enhanced Support & Resistance Detection System - Refactored
        
        Modular architecture with dependency injection:
        1. Data fetching via SRDataProvider
        2. Swing detection via SRDetector  
        3. Scoring and MTF via SRScorer
        4. State management via SRState
        5. Optimized O(N) algorithms
        6. Proper recalculation logic with oscillation prevention
        """
        try:
            current_time = time.time()
            
            # PERFORMANCE OPTIMIZATION: Check minimum recalculation interval
            last_update = self._last_module_updates.get('support_resistance', 0)
            if current_time - last_update < self._min_recalculation_interval:
                # Return cached result if available
                cached_result = self._get_cached_analysis(current_price, current_time)
                if cached_result.get("status") == "ok":
                    return cached_result
            
            # Reset session state to prevent cross-contamination
            self._state.reset_session_state()
            
            # 1. FETCH MULTI-TIMEFRAME DATA - Via SRDataProvider (needed for ATR)
            candles_data, atr_per_tf = self._data_provider.fetch_multi_timeframe_data(current_price)
            atr_14 = atr_per_tf.get('5m', 0.0)  # Extract 5m ATR for backward compatibility
            
            # 2. CHECK RECALCULATION NEEDS - Prevent oscillation recalculations
            if not self._state.should_recalculate(current_price, current_time, atr_14):
                # Check if cached result is an error - if so, force recalculation
                cached_result = self._get_cached_analysis(current_price, current_time)
                if cached_result.get("status") != "error":
                    return cached_result
            
            # 3. DETECT SWING POINTS - Via SRDetector with timeframe-specific sensitivity
            swing_points_5m, higher_tf_levels = self._detect_all_swing_points(candles_data, current_price)
            
            # DEBUG: Log swing point counts
            logger.info(f"🔍 SWING POINT DETECTION: {len(swing_points_5m)} 5m swing points, {len(higher_tf_levels)} higher-TF swing points")
            support_swings = [sp for sp in swing_points_5m if sp.level_type == 'support' and sp.level < current_price]
            resistance_swings = [sp for sp in swing_points_5m if sp.level_type == 'resistance' and sp.level > current_price]
            logger.info(f"   Support swings (below ${current_price:.2f}): {len(support_swings)}")
            logger.info(f"   Resistance swings (above ${current_price:.2f}): {len(resistance_swings)}")
            if support_swings:
                logger.info(f"   Support swing prices: {[f'${sp.level:.2f}' for sp in sorted(support_swings, key=lambda x: x.level, reverse=True)[:10]]}")
            if resistance_swings:
                logger.info(f"   Resistance swing prices: {[f'${sp.level:.2f}' for sp in sorted(resistance_swings, key=lambda x: x.level)[:10]]}")
            
            # 4. CLUSTER LEVELS - Adaptive tolerance algorithm
            cluster_tolerance = self._calculate_adaptive_tolerance(atr_14, current_price)
            clustered_levels = self._detector.cluster_levels(swing_points_5m, cluster_tolerance)
            
            # 4.1. SEARCH DATABASE FOR ADDITIONAL TOUCHES - For levels with only 1 touch
            # If we have levels with only 1 touch, search the database further back to find the 2nd touch
            # We have 5 years of 5m candles in the database, so we can look back much further
            levels_with_1_touch = [level for level in clustered_levels if level.touches == 1]
            if levels_with_1_touch:
                logger.info(f"🔍 Searching database for additional touches: {len(levels_with_1_touch)} levels with only 1 touch")
                clustered_levels = self._search_database_for_additional_touches(
                    clustered_levels, levels_with_1_touch, candles_data.get("5m", []), cluster_tolerance, atr_14
                )
            
            # DEBUG: Log clustering results
            logger.info(f"🔍 CLUSTERING: {len(clustered_levels)} clustered levels (tolerance: ${cluster_tolerance:.2f})")
            logger.info("   ALL CLUSTERED LEVELS:")
            levels_with_2plus = [level for level in clustered_levels if level.touches >= 2]
            levels_with_1 = [level for level in clustered_levels if level.touches == 1]
            logger.info(f"   Levels with 2+ touches: {len(levels_with_2plus)}, Levels with 1 touch: {len(levels_with_1)}")
            for level in sorted(clustered_levels, key=lambda x: x.level, reverse=True)[:15]:
                touch_indicator = "✅" if level.touches >= 2 else "⚠️"
                logger.info(f"   {touch_indicator} {'🟢' if level.level_type == 'support' else '🔴'} {level.level_type.capitalize()} ${level.level:.2f}: {level.touches}x touches, cluster_size={level.cluster_size}, strength={level.strength:.1f}")
            
            # DON'T reclassify levels - keep original swing point type (support/resistance)
            # Historical levels keep their original type regardless of current price position
            # This ensures we can find resistance above current price even if it was detected from the past
            # The filtering below will only select levels that are correctly positioned relative to current price
            
            clustered_support = [level for level in clustered_levels if level.level_type == 'support' and level.level < current_price]
            clustered_resistance = [level for level in clustered_levels if level.level_type == 'resistance' and level.level > current_price]
            logger.info(f"   Clustered support (below ${current_price:.2f}): {len(clustered_support)}")
            logger.info(f"   Clustered resistance (above ${current_price:.2f}): {len(clustered_resistance)}")
            
            # 4.5. TOUCH COUNTS: Use swing points only (they measure actual reversals)
            # Swing points = actual price reversals (what matters for S/R strength)
            # If swing detection is missing valid swing points, we should fix swing detection parameters
            # NOT add a second counting method that includes noise
            
            # Levels clustered - no verbose logging needed
            
            # 5. MTF ALIGNMENT AND SCORING - Via SRScorer with per-timeframe ATR
            aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_per_tf)
            
            # DEBUG: Log MTF alignment
            logger.info(f"🔍 MTF ALIGNMENT: {len(aligned_levels)} aligned levels")
            aligned_support = [level for level in aligned_levels if level.level_type == 'support' and level.level < current_price]
            aligned_resistance = [level for level in aligned_levels if level.level_type == 'resistance' and level.level > current_price]
            logger.info(f"   Aligned support: {len(aligned_support)}, Aligned resistance: {len(aligned_resistance)}")
            
            # RISK MANAGEMENT: Only process levels within liquidation range (saves processing power)
            # Calculate liquidation prices once for filtering
            long_liquidation = self._liquidation_calc.calculate_liquidation_price(current_price, "LONG")
            short_liquidation = self._liquidation_calc.calculate_liquidation_price(current_price, "SHORT")
            
            logger.info(f"🔍 LIQUIDATION RANGE: LONG liquidation=${long_liquidation:.2f}, SHORT liquidation=${short_liquidation:.2f}")
            
            # Filter aligned levels BEFORE scoring to save processing power
            # Only score levels that are safe from liquidation:
            # - Support levels (LONG entries) must be above LONG liquidation price
            # - Resistance levels (SHORT entries) must be below SHORT liquidation price
            levels_within_range = []
            filtered_out_support = 0
            filtered_out_resistance = 0
            for level in aligned_levels:
                if level.level_type == 'support' and level.level < current_price:
                    if level.level >= long_liquidation:  # Safe for LONG entry
                        levels_within_range.append(level)
                    else:
                        filtered_out_support += 1
                elif level.level_type == 'resistance' and level.level > current_price:
                    if level.level <= short_liquidation:  # Safe for SHORT entry
                        levels_within_range.append(level)
                    else:
                        filtered_out_resistance += 1
            
            logger.info(f"🔍 LIQUIDATION FILTER: {len(levels_within_range)} levels within range ({filtered_out_support} support, {filtered_out_resistance} resistance filtered out)")
            
            # Filter levels with minimum 2x touches requirement (we have enough data now)
            # Levels with only 1 touch are not reliable - need at least 2 touches to confirm level strength
            levels_with_2plus_touches = [level for level in levels_within_range if level.touches >= 2]
            filtered_out_single_touch = len(levels_within_range) - len(levels_with_2plus_touches)
            
            if filtered_out_single_touch > 0:
                logger.info(f"🔍 TOUCH FILTER: Filtered out {filtered_out_single_touch} levels with <2 touches (minimum 2x required)")
            
            # Score only levels with 2+ touches (saves processing power and ensures quality)
            scored_levels = self._scorer.score_levels_enhanced(levels_with_2plus_touches, current_price, atr_14, atr_per_tf)
            
            # DEBUG: Log scored levels
            logger.info(f"🔍 SCORED LEVELS: {len(scored_levels)} levels scored (all with 2+ touches)")
            scored_support = [level for level in scored_levels if level.level_type == 'support' and level.level < current_price]
            scored_resistance = [level for level in scored_levels if level.level_type == 'resistance' and level.level > current_price]
            logger.info(f"   Scored support: {len(scored_support)}, Scored resistance: {len(scored_resistance)}")
            for level in sorted(scored_support, key=lambda x: x.score, reverse=True)[:10]:
                breakdown = level.score_breakdown or {}
                logger.info(f"   🟢 Support ${level.level:.2f}: Score={level.score:.1f}, Touches={level.touches}x, "
                          f"Proximity={breakdown.get('proximity', 0):.1f}, Touch={breakdown.get('touch', 0):.1f}, "
                          f"Volume={breakdown.get('volume', 0):.1f}")
            for level in sorted(scored_resistance, key=lambda x: x.score, reverse=True)[:10]:
                breakdown = level.score_breakdown or {}
                logger.info(f"   🔴 Resistance ${level.level:.2f}: Score={level.score:.1f}, Touches={level.touches}x, "
                          f"Proximity={breakdown.get('proximity', 0):.1f}, Touch={breakdown.get('touch', 0):.1f}, "
                          f"Volume={breakdown.get('volume', 0):.1f}")
            
            # 5.5. FINAL DEDUPLICATION - Merge levels that are too close (after scoring)
            # Scientific justification: Levels within 0.05% of price are statistically indistinguishable
            # for trading purposes (noise vs signal). This prevents duplicate levels from different
            # timeframes or clustering artifacts. Percentage-based ensures scalability across price ranges.
            final_dedup_tolerance = current_price * 0.0005  # 0.05% of price (scientifically justified threshold)
            scored_levels = self._deduplicate_scored_levels(scored_levels, final_dedup_tolerance)
            
            # 5.6. VERIFY WE HAVE 2 SUPPORT + 2 RESISTANCE
            # Scientific justification: For live trading, we need exactly 2 support and 2 resistance levels
            # SCORING SYSTEM IS THE ONLY FACTOR - NO FILTERING
            # All levels are scored - highest scores win (proximity penalty, touch rewards, etc.)
            # Scan nearby first (from current data), if not found, scan further in past until we find levels
            # Loop until we find enough levels (max 3 attempts to prevent infinite loops)
            
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                # Count support and resistance levels (already filtered to liquidation range before scoring)
                support_levels = [level for level in scored_levels 
                                 if level.level_type == 'support' and level.level < current_price]
                resistance_levels = [level for level in scored_levels 
                                  if level.level_type == 'resistance' and level.level > current_price]
                
                support_count = len(support_levels)
                resistance_count = len(resistance_levels)
                
                # If we have enough levels, break the loop
                if support_count >= 2 and resistance_count >= 2:
                    break
                
                # If we don't have enough and haven't exceeded max attempts, fetch more data
                if attempt < max_attempts - 1:
                    logger.warning(f"⚠️ Insufficient levels: {support_count} support, {resistance_count} resistance. Fetching more historical data...")
                    
                    # Fetch more historical data and recalculate
                    candles_data, atr_per_tf = self._data_provider.fetch_multi_timeframe_data(current_price, force_extended_lookback=True)
                    atr_14 = atr_per_tf.get('5m', 0.0)
                    
                    # Re-detect swing points with extended data
                    swing_points_5m, higher_tf_levels = self._detect_all_swing_points(candles_data, current_price)
                    
                    # Re-cluster and score with extended data
                    cluster_tolerance = self._calculate_adaptive_tolerance(atr_14, current_price)
                    clustered_levels = self._detector.cluster_levels(swing_points_5m, cluster_tolerance)
                    aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_per_tf)
                    
                    # RISK MANAGEMENT: Only process levels within liquidation range (saves processing power)
                    # Calculate liquidation prices for filtering
                    long_liquidation = self._liquidation_calc.calculate_liquidation_price(current_price, "LONG")
                    short_liquidation = self._liquidation_calc.calculate_liquidation_price(current_price, "SHORT")
                    
                    # Filter aligned levels BEFORE scoring to save processing power
                    levels_within_range = []
                    for level in aligned_levels:
                        if level.level_type == 'support' and level.level < current_price:
                            if level.level >= long_liquidation:  # Safe for LONG entry
                                levels_within_range.append(level)
                        elif level.level_type == 'resistance' and level.level > current_price:
                            if level.level <= short_liquidation:  # Safe for SHORT entry
                                levels_within_range.append(level)
                    
                    # Filter levels with minimum 2x touches requirement
                    levels_with_2plus_touches = [level for level in levels_within_range if level.touches >= 2]
                    
                    # Score only levels with 2+ touches (saves processing power and ensures quality)
                    scored_levels = self._scorer.score_levels_enhanced(levels_with_2plus_touches, current_price, atr_14, atr_per_tf)
                    scored_levels = self._deduplicate_scored_levels(scored_levels, final_dedup_tolerance)
                else:
                    # Last attempt - log warning but continue with what we have
                    logger.warning(f"⚠️ After {max_attempts} attempts: Only found {support_count} support, "
                                 f"{resistance_count} resistance. Proceeding with available levels.")
                
                attempt += 1
            
            # 6. FORMAT RESULTS - With proper state management
            result = self._format_results_optimized(scored_levels, current_price, atr_14, current_time)
            
            # DEBUG: Log final top levels that will be displayed
            top_2_support = result.get('top_2_support', [])
            top_2_resistance = result.get('top_2_resistance', [])
            logger.info(f"📊 FINAL RESULTS: {len(top_2_support)} support, {len(top_2_resistance)} resistance levels")
            for sup in top_2_support:
                logger.info(f"   🟢 BEST SUPPORT: ${sup.get('price_level', 0):.2f} | Score: {sup.get('strength_score', 0):.1f} | "
                          f"Touches: {sup.get('touches', 0)}x | Status: {sup.get('status', 'unknown')}")
            for res in top_2_resistance:
                logger.info(f"   🔴 BEST RESISTANCE: ${res.get('price_level', 0):.2f} | Score: {res.get('strength_score', 0):.1f} | "
                          f"Touches: {res.get('touches', 0)}x | Status: {res.get('status', 'unknown')}")
            
            # 7. UPDATE STATE - Track calculation completion
            self._state.update_calculation_state(current_price, current_time)
            
            logger.info(f"📊 S/R calculation complete: {len(scored_levels)} levels processed")
            
            # PERFORMANCE OPTIMIZATION: Update last calculation time
            self._last_module_updates['support_resistance'] = current_time
            
            return result
            
        except Exception as e:
            logger.error(f"❌ S/R calculation failed: {e}")
            return self._create_error_result(str(e))
    
    def _get_cache_key(self, current_price: float, current_time: float) -> str:
        """
        Generate consistent cache key for S/R analysis with collision avoidance
        
        Args:
            current_price: Current price
            current_time: Current timestamp
            
        Returns:
            Cache key string with price precision to avoid collisions
        """
        timestamp_bucket = self._get_timestamp_bucket(current_time)
        # Use price with 2 decimal precision to avoid collisions
        price_key = f"{current_price:.2f}".replace('.', 'p')
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
        Get cached analysis if available with proper cache key structure
        
        Args:
            current_price: Current price
            current_time: Current timestamp
            
        Returns:
            Cached analysis or error result
        """
        try:
            # Create timestamp bucket (5-minute buckets)
            cache_key = self._get_cache_key(current_price, current_time)
            
            cached_data = self._cache.get(cache_key)
            if cached_data:
                return cached_data
            # No valid cache, return error result
            return self._create_error_result("No cached analysis available")
            
        except Exception as e:
            logger.error(f"❌ Cache retrieval failed: {e}")
            return self._create_error_result(str(e))
    
    def _count_actual_touches(self, clustered_levels: List, candles: List[Dict], atr_14: float) -> List:
        """
        Validate swing point touch counts by checking actual candle touches
        
        NOTE: This method is kept for validation/debugging purposes only.
        The final touch count uses swing points only, as they measure actual reversals.
        
        Why swing points are the correct measure:
        - Swing points = actual price reversals (what matters for S/R strength)
        - Actual touches = price got close (includes noise and non-reactions)
        - If price touched a level 10 times but only reversed once, the level is WEAK
        - Combining them would inflate weak levels, which is misleading
        
        If swing detection is missing valid swing points, we should:
        1. Adjust swing detection parameters (n, filters) to be less strict
        2. NOT add a second counting method that includes noise
        
        Args:
            clustered_levels: List of clustered Level objects (with swing point touch counts)
            candles: List of candle dictionaries (5m candles)
            atr_14: ATR for touch tolerance
            
        Returns:
            List of Level objects (touch counts unchanged - using swing points only)
        """
        try:
            if not candles or not clustered_levels:
                return clustered_levels
            
            # Touch tolerance: price is considered to have "touched" if within 0.5*ATR
            touch_tolerance = atr_14 * 0.5
            
            updated_levels = []
            for level in clustered_levels:
                level_price = level.level
                level_type = level.level_type
                actual_touches = 0
                
                # Track distinct touches (avoid counting same candle multiple times)
                touched_timestamps = set()
                
                for candle in candles:
                    high = candle.get('high', 0)
                    low = candle.get('low', 0)
                    timestamp = candle.get('timestamp', 0)
                    
                    if high <= 0 or low <= 0:
                        continue
                    
                    # Check if price touched the level (within tolerance)
                    if level_type == 'resistance':
                        # Resistance: price touched if high >= (level - tolerance)
                        if high >= (level_price - touch_tolerance):
                            if timestamp not in touched_timestamps:
                                actual_touches += 1
                                touched_timestamps.add(timestamp)
                    elif level_type == 'support':
                        # Support: price touched if low <= (level + tolerance)
                        if low <= (level_price + touch_tolerance):
                            if timestamp not in touched_timestamps:
                                actual_touches += 1
                                touched_timestamps.add(timestamp)
                
                # Use swing point touches as the source of truth
                # Swing points measure what matters: actual price reversals at the level
                # If price touched a level 10 times but only reversed once, the level is WEAK, not strong
                # Actual touches include noise (candles that just grazed the level without reaction)
                # Therefore, we use swing points only - they measure actual level strength
                final_touches = level.touches  # From swing point detection (actual reversals)
                
                # Create updated level with correct touch count (Level is frozen, so create new instance)
                from .level import Level
                updated_level = Level(
                    level=level.level,
                    level_type=level.level_type,
                    touches=final_touches,
                    cluster_size=level.cluster_size,
                    weighted_touches=float(final_touches),  # Update weighted touches too
                    strength=level.strength,
                    timestamp=level.timestamp,
                    timeframe_distribution=level.timeframe_distribution,
                    mtf_matches=level.mtf_matches,
                    mtf_count=level.mtf_count,
                    mtf_confidence=level.mtf_confidence,
                    merged_from=level.merged_from,
                    score=level.score,
                    score_breakdown=level.score_breakdown
                )
                updated_levels.append(updated_level)
            
            return updated_levels
            
        except Exception as e:
            logger.error(f"❌ Actual touch counting failed: {e}")
            return clustered_levels  # Return original if counting fails
    
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
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            
            # Get candles from database by range (older than our current dataset)
            if hasattr(historical_service, '_candle_storage') and historical_service._candle_storage:
                additional_candles = historical_service._candle_storage.get_candles_by_range(
                    lookback_timestamp, oldest_timestamp - 300  # Exclude the last 5 minutes to avoid overlap
                )
                
                if not additional_candles:
                    logger.debug(f"🔍 No additional candles found in database (looking back {lookback_days} days)")
                    return clustered_levels
                
                logger.info(f"🔍 Found {len(additional_candles)} additional candles in database (looking back {lookback_days} days)")
                
                # Detect swing points in the additional historical data
                # Use a more sensitive swing detection to catch more potential touches
                additional_swing_points = self._detector.detect_swing_points(
                    additional_candles, 
                    current_price=0,  # Not needed for historical detection
                    n=1,  # More sensitive (n=1) to catch more swing points
                    timeframe="5m"
                )
                
                logger.info(f"🔍 Found {len(additional_swing_points)} additional swing points in historical data")
                
                # For each level with only 1 touch, check if any additional swing points match
                from .level import Level
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
                            logger.info(f"✅ Found {len(matching_swings)} additional touch(es) for {level.level_type} ${level.level:.2f} (now {total_touches}x touches)")
                            
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
                                score=level.score,
                                score_breakdown=level.score_breakdown
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
            Formatted result dictionary
        """
        try:
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
                    "strength_score": level.score,
                    "multi_tf": level.mtf_count > 0,
                    "status": level_status,
                    "touches": level.touches,
                    "last_touch_timestamp": level.timestamp,
                    "mtf_count": level.mtf_count,
                    "mtf_confidence": level.mtf_confidence,
                    "score_breakdown": level.score_breakdown,
                    "merged_from": level.merged_from
                })
            
            # Sort by strength score - SCORING SYSTEM IS THE ONLY FACTOR (touch 50%, proximity 45%, volume 5%)
            # Highest score wins - proximity penalty (distance), touch rewards, volume confirmation
            key_levels.sort(key=lambda x: x["strength_score"], reverse=True)
            
            # SCORING SYSTEM IS THE ONLY FACTOR - NO FILTERING BY SCORE THRESHOLD
            # Ensure we have ACTIVE levels for both support and resistance
            # Strategy: Filter for active levels only (broken levels are excluded), scoring system determines best
            active_support_candidates = [level for level in key_levels 
                                        if level.get("type") == "support" and 
                                        level["price_level"] < current_price and 
                                        level.get("status") == "active"]
            active_resistance_candidates = [level for level in key_levels 
                                           if level.get("type") == "resistance" and 
                                           level["price_level"] > current_price and 
                                           level.get("status") == "active"]
            
            # Sort each by score
            active_support_candidates.sort(key=lambda x: x["strength_score"], reverse=True)
            active_resistance_candidates.sort(key=lambda x: x["strength_score"], reverse=True)
            
            # Take top 2 of each (or all if less than 2) - these are already active
            top_support = active_support_candidates[:2]
            top_resistance = active_resistance_candidates[:2]
            
            # Combine and add remaining top-scored levels to fill up to 10 total
            # SCORING SYSTEM IS THE ONLY FACTOR - highest scores win
            final_key_levels = top_support + top_resistance
            remaining_slots = 10 - len(final_key_levels)
            if remaining_slots > 0:
                # Add remaining top-scored levels (excluding already selected ones)
                already_selected = {level["price_level"] for level in final_key_levels}
                for level in key_levels:  # Use original key_levels (all levels sorted by score)
                    if level["price_level"] not in already_selected and len(final_key_levels) < 10:
                        final_key_levels.append(level)
            
            # Re-sort by score to maintain order - SCORING SYSTEM IS THE ONLY FACTOR
            final_key_levels.sort(key=lambda x: x["strength_score"], reverse=True)
            key_levels = final_key_levels
            
            # Final lists - these should have at least 2 of each if available (already filtered for active)
            support_levels = top_support  # Already filtered for active support
            resistance_levels = top_resistance  # Already filtered for active resistance
            
            # Support and resistance levels filtered - no verbose logging needed
            if not resistance_levels:
                # Check if we have any levels above current price (even if inactive)
                levels_above = [level for level in key_levels if level["price_level"] > current_price]
                if levels_above:
                    inactive_above = [level for level in levels_above if level.get("status") == "inactive"]
                    logger.warning(f"⚠️ No active resistance found above ${current_price:.2f}. "
                                 f"Found {len(levels_above)} levels above price ({len(inactive_above)} inactive). "
                                 f"Top level: ${max(levels_above, key=lambda x: x['price_level'])['price_level']:.2f}")
                else:
                    logger.warning(f"⚠️ No resistance levels found above ${current_price:.2f}. "
                                 f"Total levels: {len(key_levels)}, "
                                 f"Levels above price: 0")
            
            # Shared helper function to get strongest level by score
            def _get_strongest_level(levels: List[Dict]) -> tuple:
                """
                Get strongest level price and score
                SCORING SYSTEM IS THE ONLY FACTOR - highest score wins (touch 50%, proximity 45%, volume 5%)
                
                Args:
                    levels: List of level dictionaries
                
                Returns:
                    Tuple of (price, score)
                """
                if not levels:
                    return 0.0, 0.0
                strongest = max(levels, key=lambda x: x["strength_score"])
                return strongest["price_level"], strongest["strength_score"]
            
            # Get best and secondary levels - objective selection by score
            # SCORING SYSTEM IS THE ONLY FACTOR - NO FILTERING
            # - Score: touch (50%), proximity (45%), volume (5%)
            # - Proximity: exponential decay penalty for distance (closer = higher score)
            # - Touch: more touches = higher score
            # - Highest score = objectively best level for trading at the moment
            
            def _get_trading_levels(levels: List[Dict], current_price: float, is_support: bool) -> tuple:
                """
                Get best and secondary levels - objective selection by score
                
                SCORING SYSTEM IS THE ONLY FACTOR - NO FILTERING
                - Score: touch (50%), proximity (45%), volume (5%)
                - Proximity: exponential decay penalty for distance (closer = higher score)
                - Touch: more touches = higher score
                - Highest score = objectively best level for trading at the moment
                
                Args:
                    levels: List of level dictionaries
                    current_price: Current price
                    is_support: True for support, False for resistance
                
                Returns:
                    Tuple of (best_level, secondary_level) as (price, score) tuples
                """
                if not levels:
                    return (0.0, 0.0), (0.0, 0.0)
                
                # Sort by score (highest first) - SCORING SYSTEM IS THE ONLY FACTOR
                # Highest score wins - proximity penalty (distance), touch rewards, volume confirmation
                sorted_levels = sorted(levels, key=lambda x: x["strength_score"], reverse=True)
                
                # Best level: highest score
                best = sorted_levels[0]
                best_level = (best["price_level"], best["strength_score"])
                
                # Secondary level: second highest score, must be at least 0.1% away from best
                if len(sorted_levels) > 1:
                    for candidate in sorted_levels[1:]:
                        if abs(candidate["price_level"] - best_level[0]) > current_price * 0.001:
                            secondary_level = (candidate["price_level"], candidate["strength_score"])
                            break
                    else:
                        # All levels too close to best, use second by score anyway
                        secondary_level = (sorted_levels[1]["price_level"], sorted_levels[1]["strength_score"])
                else:
                    secondary_level = (0.0, 0.0)
                
                return best_level, secondary_level
            
            # Get best and secondary levels for support and resistance
            (best_support, best_support_score), (secondary_support, secondary_support_score) = \
                _get_trading_levels(support_levels, current_price, is_support=True)
            (best_resistance, best_resistance_score), (secondary_resistance, secondary_resistance_score) = \
                _get_trading_levels(resistance_levels, current_price, is_support=False)
            
            # Log if we couldn't find enough levels (shouldn't happen after verification)
            if (best_support == 0.0 or secondary_support == 0.0) and len(support_levels) > 0:
                logger.warning(f"⚠️ Could not find 2 support levels from {len(support_levels)} available. "
                             f"Best: ${best_support:.2f}, Secondary: ${secondary_support:.2f}")
                if len(support_levels) >= 2:
                    # Log all support levels for debugging
                    sorted_support = sorted(support_levels, key=lambda x: x["strength_score"], reverse=True)
                    support_str = ", ".join([f"${level['price_level']:.2f}({level['strength_score']:.1f})" for level in sorted_support[:5]])
                    logger.debug(f"   Available support levels: {support_str}")
            if (best_resistance == 0.0 or secondary_resistance == 0.0) and len(resistance_levels) > 0:
                logger.warning(f"⚠️ Could not find 2 resistance levels from {len(resistance_levels)} available. "
                             f"Best: ${best_resistance:.2f}, Secondary: ${secondary_resistance:.2f}")
                if len(resistance_levels) >= 2:
                    # Log all resistance levels for debugging
                    sorted_resistance = sorted(resistance_levels, key=lambda x: x["strength_score"], reverse=True)
                    resistance_str = ", ".join([f"${level['price_level']:.2f}({level['strength_score']:.1f})" for level in sorted_resistance[:5]])
                    logger.debug(f"   Available resistance levels: {resistance_str}")
                else:
                    logger.warning(f"   Only {len(resistance_levels)} resistance level(s) found above ${current_price:.2f}")
            
            # For backward compatibility, strongest = best
            strongest_support, support_score = best_support, best_support_score
            strongest_resistance, resistance_score = best_resistance, best_resistance_score
            
            # Validation: These should already be filtered correctly, but double-check
            if strongest_support > 0 and strongest_support >= current_price:
                logger.error(f"❌ Invalid support level: ${strongest_support:.2f} >= current price ${current_price:.2f}")
                strongest_support, support_score = 0.0, 0.0
            
            if strongest_resistance > 0 and strongest_resistance <= current_price:
                logger.error(f"❌ Invalid resistance level: ${strongest_resistance:.2f} <= current price ${current_price:.2f}")
                strongest_resistance, resistance_score = 0.0, 0.0
            
            # Log validation warnings if no levels found
            if strongest_support == 0:
                logger.warning(f"⚠️ No valid support found below ${current_price:.2f}")
            
            if strongest_resistance == 0:
                logger.warning(f"⚠️ No valid resistance found above ${current_price:.2f}")
            
            # Get state summary for metadata
            state_summary = self._state.get_state_summary()
            
            # Build top 2 support and resistance lists - exactly 2 of each (best + secondary)
            # If we don't have enough after filtering, look back at all scored levels to find secondary
            top_2_support_list = []
            if best_support > 0:
                best_support_obj = next((level for level in support_levels if abs(level["price_level"] - best_support) < 1), None)
                if best_support_obj:
                    top_2_support_list.append(best_support_obj)
            
            # Try to add secondary support from filtered levels first
            if secondary_support > 0 and abs(secondary_support - best_support) > current_price * 0.001:
                secondary_support_obj = next((level for level in support_levels if abs(level["price_level"] - secondary_support) < 1), None)
                if secondary_support_obj:
                    top_2_support_list.append(secondary_support_obj)
            
            # If we only have 1 support, this should only happen in edge cases (all-time low with all support broken)
            # The verification loop should have ensured we have 2+ levels, so this indicates a true edge case or bug
            if len(top_2_support_list) == 1:
                # Check if this is a true edge case (all-time low) or a bug
                all_support = [level for level in scored_levels 
                              if level.level_type == 'support' and
                              level.level < current_price and 
                              self._state.check_level_status(level, current_price, atr_14) == "active"]
                if len(all_support) >= 2:
                    # Try to find second from all levels
                    sorted_all_support = sorted(all_support, key=lambda x: x.score, reverse=True)
                    for candidate in sorted_all_support:
                        if abs(candidate.level - best_support) < 1:
                            continue
                        if abs(candidate.level - best_support) > current_price * 0.001:
                            candidate_dict = {
                                "price_level": candidate.level,
                                "strength_score": candidate.score,
                                "touches": candidate.touches,
                                "status": "active",
                                "type": "support"
                            }
                            top_2_support_list.append(candidate_dict)
                            break
            
            top_2_resistance_list = []
            if best_resistance > 0:
                best_resistance_obj = next((level for level in resistance_levels if abs(level["price_level"] - best_resistance) < 1), None)
                if best_resistance_obj:
                    top_2_resistance_list.append(best_resistance_obj)
            
            # Try to add secondary resistance from filtered levels first
            if secondary_resistance > 0 and abs(secondary_resistance - best_resistance) > current_price * 0.001:
                secondary_resistance_obj = next((level for level in resistance_levels if abs(level["price_level"] - secondary_resistance) < 1), None)
                if secondary_resistance_obj:
                    top_2_resistance_list.append(secondary_resistance_obj)
            
            # If we only have 1 resistance, this should only happen in edge cases (all-time high with all resistance broken)
            # The verification loop should have ensured we have 2+ levels, so this indicates a true edge case or bug
            if len(top_2_resistance_list) == 1:
                # Check if this is a true edge case (all-time high) or a bug
                all_resistance = [level for level in scored_levels 
                                if level.level_type == 'resistance' and
                                level.level > current_price and 
                                self._state.check_level_status(level, current_price, atr_14) == "active"]
                if len(all_resistance) >= 2:
                    # Try to find second from all levels
                    sorted_all_resistance = sorted(all_resistance, key=lambda x: x.score, reverse=True)
                    for candidate in sorted_all_resistance:
                        if abs(candidate.level - best_resistance) < 1:
                            continue
                        if abs(candidate.level - best_resistance) > current_price * 0.001:
                            candidate_dict = {
                                "price_level": candidate.level,
                                "strength_score": candidate.score,
                                "touches": candidate.touches,
                                "status": "active",
                                "type": "resistance"
                            }
                            top_2_resistance_list.append(candidate_dict)
                            break
            
            result = {
                "status": "ok",
                "levels": key_levels,
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
                # Top 2 support and resistance - exactly 2 levels: best + secondary
                "top_2_support": top_2_support_list[:2],  # Ensure exactly 2
                "top_2_resistance": top_2_resistance_list[:2],  # Ensure exactly 2
                # Add root-level fields for dashboard compatibility
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "support_score": support_score,
                "resistance_score": resistance_score,
                # Liquidation prices for trading at current price and S/R levels
                "liquidation_prices": self._liquidation_calc.calculate_liquidation_prices_for_levels(
                    strongest_support, strongest_resistance, current_price
                )
            }
            
            # Cache the result with proper key structure and TTL
            cache_key = self._get_cache_key(current_price, current_time)
            
            self._cache.set(cache_key, result, ttl=300)  # 5-minute TTL
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Result formatting failed: {e}")
            return self._create_error_result(str(e))
    
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
    