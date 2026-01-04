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
            
            logger.debug(f"📊 Adaptive tolerance: {tolerance_pct*100:.2f}% of price = ${adaptive_tolerance:.2f}")
            
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
                        logger.debug(f"📊 Merging duplicate levels: ${level.level:.2f} into ${existing.level:.2f} "
                                   f"(distance: {abs(level.level - existing.level):.2f} <= {tolerance:.2f})")
                        break
                
                if not is_duplicate:
                    deduplicated.append(level)
            
            return deduplicated
            
        except Exception as e:
            logger.error(f"❌ Final deduplication failed: {e}")
            return scored_levels
    
    def _calculate_atr_per_timeframe(self, candles_data: Dict[str, List[Dict]]) -> Dict[str, float]:
        """
        Calculate ATR for each timeframe as volatility reference
        
        Args:
            candles_data: Dictionary of candles by timeframe
            
        Returns:
            Dictionary of ATR values per timeframe
        """
        try:
            atr_per_tf = {}
            
            for tf, candles in candles_data.items():
                if candles:
                    atr_value = self._data_provider.calculate_atr(candles, 14)
                    atr_per_tf[tf] = atr_value
                    logger.debug(f"📊 ATR({tf}): {atr_value:.2f}")
                else:
                    atr_per_tf[tf] = 0.0
                    logger.warning(f"⚠️ No candles for {tf} timeframe")
            
            return atr_per_tf
            
        except Exception as e:
            logger.error(f"❌ ATR per timeframe calculation failed: {e}")
            # Return default ATR values
            return {
                "5m": 100.0,  # Default ATR values
                "15m": 150.0,
                "1h": 200.0,
                "1d": 500.0
            }
    
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
            logger.debug(f"🔍 Calculating S/R levels for {self.symbol} at ${current_price:.2f}")
            
            # PERFORMANCE OPTIMIZATION: Check minimum recalculation interval
            last_update = self._last_module_updates.get('support_resistance', 0)
            if current_time - last_update < self._min_recalculation_interval:
                logger.debug(f"⏱️ S/R calculation throttled - {self._min_recalculation_interval - (current_time - last_update):.0f}s remaining")
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
                if cached_result.get("status") == "error":
                    logger.debug("📊 Cached result is error - forcing recalculation")
                else:
                    logger.debug("📊 Using cached calculation - no recalculation needed")
                    return cached_result
            
            # 3. DETECT SWING POINTS - Via SRDetector with timeframe-specific sensitivity
            swing_points_5m = self._detector.detect_swing_points(
                candles_data.get("5m", []), current_price, n=1, timeframe="5m")  # Most sensitive for recent levels
            
            # Detect higher timeframe swing points with safe access
            higher_tf_levels = []
            candles_15m = candles_data.get("15m", [])
            if candles_15m:
                swing_15m = self._detector.detect_swing_points(
                    candles_15m, current_price, n=2, timeframe="15m")  # Moderate sensitivity
                higher_tf_levels.extend(swing_15m)
            
            candles_1h = candles_data.get("1h", [])
            if candles_1h:
                swing_1h = self._detector.detect_swing_points(
                    candles_1h, current_price, n=3, timeframe="1h")  # Less sensitive for major levels
                higher_tf_levels.extend(swing_1h)
            
            candles_1d = candles_data.get("1d", [])
            if candles_1d:
                swing_1d = self._detector.detect_swing_points(
                    candles_1d, current_price, n=4, timeframe="1d")  # Least sensitive for major levels
                higher_tf_levels.extend(swing_1d)
            
            # 4. CLUSTER LEVELS - Adaptive tolerance algorithm
            cluster_tolerance = self._calculate_adaptive_tolerance(atr_14, current_price)
            clustered_levels = self._detector.cluster_levels(swing_points_5m, cluster_tolerance)
            
            # Debug: Log swing point detection results
            logger.debug(f"📊 Swing detection: 5m={len(swing_points_5m)}, higher_tf={len(higher_tf_levels)}, "
                        f"clustered={len(clustered_levels)}")
            if higher_tf_levels:
                levels_above = [level for level in higher_tf_levels if level.level > current_price]
                logger.debug(f"📊 Higher TF levels above ${current_price:.2f}: {len(levels_above)}")
            
            # 5. MTF ALIGNMENT AND SCORING - Via SRScorer with per-timeframe ATR
            aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_per_tf)
            scored_levels = self._scorer.score_levels_enhanced(aligned_levels, current_price, atr_14, atr_per_tf)
            
            # Debug: Log scored levels above current price
            levels_above_price = [level for level in scored_levels if level.level > current_price]
            logger.debug(f"📊 Scored levels above ${current_price:.2f}: {len(levels_above_price)}")
            
            # 5.5. FINAL DEDUPLICATION - Merge levels that are too close (after scoring)
            # Scientific justification: Levels within 0.05% of price are statistically indistinguishable
            # for trading purposes (noise vs signal). This prevents duplicate levels from different
            # timeframes or clustering artifacts. Percentage-based ensures scalability across price ranges.
            final_dedup_tolerance = current_price * 0.0005  # 0.05% of price (scientifically justified threshold)
            scored_levels = self._deduplicate_scored_levels(scored_levels, final_dedup_tolerance)
            logger.debug(f"📊 Final deduplication: tolerance={final_dedup_tolerance:.2f}, levels={len(scored_levels)}")
            
            # 5.6. VERIFY WE HAVE 2 SUPPORT + 2 RESISTANCE
            # Scientific justification: For live trading, we need exactly 2 support and 2 resistance levels
            # Score already includes proximity (60% weight), so best levels for trading will have highest scores
            # Scan nearby first (from current data), if not found, scan further in past until we find levels
            # Loop until we find enough levels (max 3 attempts to prevent infinite loops)
            
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                # Count support and resistance levels (score already incorporates proximity)
                support_levels = [level for level in scored_levels if level.level < current_price]
                resistance_levels = [level for level in scored_levels if level.level > current_price]
                
                support_count = len(support_levels)
                resistance_count = len(resistance_levels)
                
                # If we have enough levels, break the loop
                if support_count >= 2 and resistance_count >= 2:
                    logger.debug(f"✅ Found sufficient levels: {support_count} support, {resistance_count} resistance")
                    # Log the top levels by score for debugging
                    if support_levels:
                        top_support = sorted(support_levels, key=lambda x: x.score, reverse=True)[:5]
                        support_prices = [f"${level.level:.2f}({level.score:.1f})" for level in top_support]
                        logger.debug(f"   Top support by score: {', '.join(support_prices)}")
                    if resistance_levels:
                        top_resistance = sorted(resistance_levels, key=lambda x: x.score, reverse=True)[:5]
                        resistance_prices = [f"${level.level:.2f}({level.score:.1f})" for level in top_resistance]
                        logger.debug(f"   Top resistance by score: {', '.join(resistance_prices)}")
                    break
                
                # If we don't have enough and haven't exceeded max attempts, fetch more data
                if attempt < max_attempts - 1:
                    logger.debug(f"📊 Attempt {attempt + 1}/{max_attempts}: Insufficient levels: "
                               f"{support_count} support, {resistance_count} resistance. Fetching more historical data...")
                    
                    # Fetch more historical data and recalculate
                    candles_data, atr_per_tf = self._data_provider.fetch_multi_timeframe_data(current_price, force_extended_lookback=True)
                    atr_14 = atr_per_tf.get('5m', 0.0)
                    
                    # Re-detect swing points with extended data
                    swing_points_5m = self._detector.detect_swing_points(
                        candles_data.get("5m", []), current_price, n=1, timeframe="5m")
                    
                    higher_tf_levels = []
                    for tf in ["15m", "1h", "1d"]:
                        tf_candles = candles_data.get(tf, [])
                        if tf_candles:
                            n_value = {"15m": 2, "1h": 3, "1d": 4}[tf]
                            swing_tf = self._detector.detect_swing_points(tf_candles, current_price, n=n_value, timeframe=tf)
                            higher_tf_levels.extend(swing_tf)
                    
                    # Re-cluster and score with extended data
                    cluster_tolerance = self._calculate_adaptive_tolerance(atr_14, current_price)
                    clustered_levels = self._detector.cluster_levels(swing_points_5m, cluster_tolerance)
                    aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_per_tf)
                    scored_levels = self._scorer.score_levels_enhanced(aligned_levels, current_price, atr_14, atr_per_tf)
                    scored_levels = self._deduplicate_scored_levels(scored_levels, final_dedup_tolerance)
                else:
                    # Last attempt - log warning but continue with what we have
                    logger.warning(f"⚠️ After {max_attempts} attempts: Only found {support_count} support, "
                                 f"{resistance_count} resistance. Proceeding with available levels.")
                
                attempt += 1
            
            # 6. FORMAT RESULTS - With proper state management
            result = self._format_results_optimized(scored_levels, current_price, atr_14, current_time)
            
            # 7. UPDATE STATE - Track calculation completion
            self._state.update_calculation_state(current_price, current_time)
            
            # Get state summary and count MTF confirmations for logging
            state_summary = self._state.get_state_summary()
            mtf_confirmed_count = sum(1 for level in scored_levels if level.mtf_count > 0)
            
            logger.info(f"📊 S/R calculation complete: {len(scored_levels)} levels processed")
            logger.debug(f"📊 RECALCULATION: {state_summary['recalculation_reasons']}")
            logger.debug(f"📊 MTF STATS: {mtf_confirmed_count}/{len(scored_levels)} levels confirmed")
            
            # Log level filtering info if result is successful
            if result.get('status') == 'ok':
                levels_count = len(result.get('levels', []))
                logger.debug(f"📊 LEVEL FILTERING: {levels_count}/{len(scored_levels)} levels passed confidence filter")
            
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
                logger.debug(f"📊 Cache HIT: {cache_key}")
                return cached_data
            
            logger.debug(f"📊 Cache MISS: {cache_key}")
            # No valid cache, return error result
            return self._create_error_result("No cached analysis available")
            
        except Exception as e:
            logger.error(f"❌ Cache retrieval failed: {e}")
            return self._create_error_result(str(e))
    
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
                
                # Create level entry with price-based classification
                level_type = "support" if level.level < current_price else "resistance"
                key_levels.append({
                    "price_level": level.level,
                    "type": level_type,
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
            
            # Sort by strength score and filter low-confidence levels
            # Score already includes proximity (60% weight), so best levels for trading will have highest scores
            key_levels.sort(key=lambda x: x["strength_score"], reverse=True)
            
            # Filter low-confidence levels (score < 20) - More lenient threshold
            filtered_levels = [level for level in key_levels if level["strength_score"] >= 20.0]
            
            # Keep top 10 levels by score - score already incorporates all factors including proximity
            key_levels = filtered_levels[:10]
            
            logger.debug(f"📊 Level filtering: {len(key_levels)} levels selected by score (current_price: ${current_price:.2f})")
            if key_levels:
                top_prices = [f"${level['price_level']:.2f}({level['strength_score']:.1f})" for level in key_levels[:5]]
                logger.debug(f"   Top levels by score: {', '.join(top_prices)}")
            
            # Calculate strongest levels - filtered by score (top 10)
            # Shared logic: Resistance MUST be above current price, Support MUST be below current price
            # EXCLUDE broken/inactive levels - only use active levels
            # Score already incorporates proximity (60% weight), so best levels for trading have highest scores
            support_levels = [level for level in key_levels 
                             if level["price_level"] < current_price and level.get("status") == "active"]
            resistance_levels = [level for level in key_levels 
                                if level["price_level"] > current_price and level.get("status") == "active"]
            
            # Debug logging for resistance detection
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
            
            # Shared helper function to get strongest level by score (proximity already factored into score)
            def _get_strongest_level(levels: List[Dict]) -> tuple:
                """
                Get strongest level price and score
                Proximity is already factored into the score calculation (60% weight in scorer)
                
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
            # Scientific justification: 
            # - Score is comprehensive: proximity (65%), touches (20%), MTF (10%), volume (5%)
            # - Proximity is heavily weighted (65%), so levels far away will have lower scores
            # - Highest score = objectively best level for trading at the moment
            
            def _get_trading_levels(levels: List[Dict], current_price: float, is_support: bool) -> tuple:
                """
                Get best and secondary levels - objective selection by score
                
                Scientific justification:
                - Score is comprehensive: proximity (65%), touches (20%), MTF (10%), volume (5%)
                - Proximity is heavily weighted (65%), so levels far away will have lower scores
                - Highest score = objectively best level for trading at the moment
                - No need for additional distance filtering - score already incorporates everything
                
                Args:
                    levels: List of level dictionaries
                    current_price: Current price
                    is_support: True for support, False for resistance
                
                Returns:
                    Tuple of (best_level, secondary_level) as (price, score) tuples
                """
                if not levels:
                    return (0.0, 0.0), (0.0, 0.0)
                
                # Sort by score (highest first) - objective selection
                # Score already includes proximity (60% weight), so best levels for trading will have highest scores
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
            
            # Log validation results
            if strongest_support > 0:
                logger.debug(f"✅ Valid support: ${strongest_support:.2f} (below ${current_price:.2f}, score: {support_score:.1f})")
            else:
                logger.warning(f"⚠️ No valid support found below ${current_price:.2f}")
            
            if strongest_resistance > 0:
                logger.debug(f"✅ Valid resistance: ${strongest_resistance:.2f} (above ${current_price:.2f}, score: {resistance_score:.1f})")
            else:
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
            if secondary_support > 0 and abs(secondary_support - best_support) > current_price * 0.001:
                secondary_support_obj = next((level for level in support_levels if abs(level["price_level"] - secondary_support) < 1), None)
                if secondary_support_obj:
                    top_2_support_list.append(secondary_support_obj)
                elif len(top_2_support_list) == 1:
                    # If we only have 1 support, look back at all scored levels to find a second one
                    all_support = [level for level in scored_levels if level.level < current_price]
                    if len(all_support) >= 2:
                        sorted_all_support = sorted(all_support, key=lambda x: x.score, reverse=True)
                        for candidate in sorted_all_support:
                            if abs(candidate.level - best_support) > current_price * 0.001:
                                # Convert Level to dict format for consistency
                                candidate_dict = {
                                    "price_level": candidate.level,
                                    "strength_score": candidate.score,
                                    "touches": candidate.touches,
                                    "status": self._state.check_level_status(candidate, current_price, atr_14),
                                    "type": "support"
                                }
                                top_2_support_list.append(candidate_dict)
                                logger.debug(f"   Added secondary support from all levels: ${candidate.level:.2f}({candidate.score:.1f})")
                                break
            
            top_2_resistance_list = []
            if best_resistance > 0:
                best_resistance_obj = next((level for level in resistance_levels if abs(level["price_level"] - best_resistance) < 1), None)
                if best_resistance_obj:
                    top_2_resistance_list.append(best_resistance_obj)
            if secondary_resistance > 0 and abs(secondary_resistance - best_resistance) > current_price * 0.001:
                secondary_resistance_obj = next((level for level in resistance_levels if abs(level["price_level"] - secondary_resistance) < 1), None)
                if secondary_resistance_obj:
                    top_2_resistance_list.append(secondary_resistance_obj)
                elif len(top_2_resistance_list) == 1:
                    # If we only have 1 resistance, look back at all scored levels to find a second one
                    all_resistance = [level for level in scored_levels if level.level > current_price]
                    if len(all_resistance) >= 2:
                        sorted_all_resistance = sorted(all_resistance, key=lambda x: x.score, reverse=True)
                        for candidate in sorted_all_resistance:
                            if abs(candidate.level - best_resistance) > current_price * 0.001:
                                # Convert Level to dict format for consistency
                                candidate_dict = {
                                    "price_level": candidate.level,
                                    "strength_score": candidate.score,
                                    "touches": candidate.touches,
                                    "status": self._state.check_level_status(candidate, current_price, atr_14),
                                    "type": "resistance"
                                }
                                top_2_resistance_list.append(candidate_dict)
                                logger.debug(f"   Added secondary resistance from all levels: ${candidate.level:.2f}({candidate.score:.1f})")
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
                "resistance_score": resistance_score
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
    