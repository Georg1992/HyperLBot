#!/usr/bin/env python3
"""
Enhanced Support/Resistance Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

import time
from typing import Dict, List, Any, Tuple, Optional, TYPE_CHECKING
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
        
        logger.info(f"📊 Refactored S/R Calculator initialized for {symbol} - Modular architecture")
    
    def _calculate_adaptive_tolerance(self, atr_14: float, current_price: float) -> float:
        """
        Calculate adaptive cluster tolerance using ATR and price percentage
        
        Args:
            atr_14: 14-period ATR
            current_price: Current price
            
        Returns:
            Adaptive tolerance value
        """
        try:
            # Base tolerance from ATR (tighter clustering)
            atr_tolerance = atr_14 * 0.4
            
            # Price percentage tolerance (0.2% of current price)
            price_tolerance = current_price * 0.002
            
            # Use the maximum of both to avoid over-merging
            adaptive_tolerance = max(atr_tolerance, price_tolerance)
            
            logger.debug(f"📊 Adaptive tolerance: ATR={atr_tolerance:.2f}, Price%={price_tolerance:.2f}, "
                        f"Final={adaptive_tolerance:.2f}")
            
            return adaptive_tolerance
            
        except Exception as e:
            logger.error(f"❌ Adaptive tolerance calculation failed: {e}")
            return atr_14 * 0.4  # Fallback to ATR-based tolerance
    
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
            
            # 5. MTF ALIGNMENT AND SCORING - Via SRScorer with per-timeframe ATR
            aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_per_tf)
            scored_levels = self._scorer.score_levels_enhanced(aligned_levels, current_price, atr_14, atr_per_tf)
            
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
    
    def _format_results_optimized(self, scored_levels: List[Dict], current_price: float, 
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
            key_levels.sort(key=lambda x: x["strength_score"], reverse=True)
            
            # Filter low-confidence levels (score < 30) - Balanced threshold
            filtered_levels = [level for level in key_levels if level["strength_score"] >= 30.0]
            
            # Keep top 10 levels per timeframe for performance
            key_levels = filtered_levels[:10]
            
            # Calculate strongest levels AFTER distance filtering
            support_levels = [level for level in key_levels if level["price_level"] < current_price]
            resistance_levels = [level for level in key_levels if level["price_level"] > current_price]
            
            strongest_support = max(support_levels, key=lambda x: x["strength_score"])["price_level"] if support_levels else 0.0
            strongest_resistance = max(resistance_levels, key=lambda x: x["strength_score"])["price_level"] if resistance_levels else 0.0
            support_score = max(support_levels, key=lambda x: x["strength_score"])["strength_score"] if support_levels else 0.0
            resistance_score = max(resistance_levels, key=lambda x: x["strength_score"])["strength_score"] if resistance_levels else 0.0
            
            # Get state summary for metadata
            state_summary = self._state.get_state_summary()
            
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
                "top_2_support": sorted([level for level in key_levels 
                                        if level["price_level"] < current_price],
                                       key=lambda x: (-x["strength_score"], abs(x["price_level"] - current_price)))[:2],
                "top_2_resistance": sorted([level for level in key_levels 
                                          if level["price_level"] > current_price],
                                         key=lambda x: (-x["strength_score"], abs(x["price_level"] - current_price)))[:2],
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
    