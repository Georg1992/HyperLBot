#!/usr/bin/env python3
"""
Enhanced Support/Resistance Calculator - Refactored Version
Modular architecture with dependency injection and optimized performance
"""

import time
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger

# Import modular components
from .sr_data_provider import SRDataProvider
from .sr_detector import SRDetector
from .sr_scorer import SRScorer
from .sr_state import SRState
from .base_calculator import BaseCalculator


class SupportResistanceCalculator(BaseCalculator):
    """Enhanced Support/Resistance calculator with dynamic recalculation and MTF integration"""
    
    def __init__(self, symbol: str = "BTC", data_provider: Optional[SRDataProvider] = None,
                 detector: Optional[SRDetector] = None, scorer: Optional[SRScorer] = None,
                 state_manager: Optional[SRState] = None):
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
        
        # Dependency injection with defaults
        self._data_provider = data_provider or SRDataProvider(symbol)
        self._detector = detector or SRDetector()
        self._scorer = scorer or SRScorer()
        self._state = state_manager or SRState()
        
        logger.info(f"📊 Refactored S/R Calculator initialized for {symbol} - Modular architecture")
    
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
            
            # 1. CHECK RECALCULATION NEEDS - Prevent oscillation recalculations
            if not self._state.should_recalculate(current_price, current_time, 0.0):
                # Check if cached result is an error - if so, force recalculation
                cached_result = self._get_cached_analysis(current_price, current_time)
                if cached_result.get("status") == "error":
                    logger.debug("📊 Cached result is error - forcing recalculation")
                else:
                    logger.debug("📊 Using cached calculation - no recalculation needed")
                    return cached_result
            
            # 2. FETCH MULTI-TIMEFRAME DATA - Via SRDataProvider
            candles_data, atr_14 = self._data_provider.fetch_multi_timeframe_data(current_price)
            
            # 3. DETECT SWING POINTS - Via SRDetector with adaptive algorithms
            swing_points_5m = self._detector.detect_swing_points(
                candles_data["5m"], current_price, n=2, timeframe="5m")
            
            # Detect higher timeframe swing points
            higher_tf_levels = []
            if candles_data["15m"]:
                swing_15m = self._detector.detect_swing_points(
                    candles_data["15m"], current_price, n=3, timeframe="15m")
                higher_tf_levels.extend(swing_15m)
            
            if candles_data["1h"]:
                swing_1h = self._detector.detect_swing_points(
                    candles_data["1h"], current_price, n=4, timeframe="1h")
                higher_tf_levels.extend(swing_1h)
            
            # 4. CLUSTER LEVELS - Optimized O(N) algorithm
            # Increased tolerance to properly cluster nearby levels (was 0.5, now 0.8)
            cluster_tolerance = atr_14 * 0.8
            clustered_levels = self._detector.cluster_levels(swing_points_5m, cluster_tolerance)
            
            # 5. MTF ALIGNMENT AND SCORING - Via SRScorer
            atr_15m = self._data_provider._calculate_atr(candles_data["15m"], 14) if candles_data["15m"] else atr_14
            aligned_levels = self._scorer.align_mtf_levels(clustered_levels, higher_tf_levels, atr_15m)
            scored_levels = self._scorer.score_levels_enhanced(aligned_levels, current_price, atr_14, atr_15m)
            
            # 6. FORMAT RESULTS - With proper state management
            result = self._format_results_optimized(scored_levels, current_price, atr_14, current_time)
            
            # 7. UPDATE STATE - Track calculation completion
            self._state.update_calculation_state(current_price, current_time)
            
            logger.info(f"📊 S/R calculation complete: {len(scored_levels)} levels processed")
            return result
            
        except Exception as e:
            logger.error(f"❌ S/R calculation failed: {e}")
            return self._create_error_result(str(e))
    
    def _get_cached_analysis(self, current_price: float, current_time: float) -> Dict[str, Any]:
        """
        Get cached analysis if available
        
        Args:
            current_price: Current price
            current_time: Current timestamp
            
        Returns:
            Cached analysis or error result
        """
        try:
            cache_key = f"sr_analysis_{self.symbol}_{current_price:.0f}"
            cached_data = self._cache.get(cache_key)
            
            if cached_data and (current_time - cached_data.get('timestamp', 0)) < 300:  # 5 min cache
                logger.debug("📊 Using cached S/R analysis")
                return cached_data
            
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
            # Separate support and resistance
            support_levels = [level for level in scored_levels if level["type"] == "support"]
            resistance_levels = [level for level in scored_levels if level["type"] == "resistance"]
            
            # Find strongest levels
            strongest_support = max(support_levels, key=lambda x: x["score"])["level"] if support_levels else 0.0
            strongest_resistance = max(resistance_levels, key=lambda x: x["score"])["level"] if resistance_levels else 0.0
            support_score = max(support_levels, key=lambda x: x["score"])["score"] if support_levels else 0.0
            resistance_score = max(resistance_levels, key=lambda x: x["score"])["score"] if resistance_levels else 0.0
            
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
                if level.get('mtf_count', 0) > 0:
                    mtf_confirmed_count += 1
                
                # Create level entry
                key_levels.append({
                    "price_level": level["level"],
                    "type": level["type"],
                    "strength_score": level["score"],
                    "multi_tf": level.get('mtf_count', 0) > 0,
                    "status": level_status,
                    "touches": level.get("touches", 0),
                    "last_touch_timestamp": level.get("timestamp", current_time),
                    "mtf_count": level.get("mtf_count", 0),
                    "mtf_confidence": level.get("mtf_confidence", 0.0),
                    "score_breakdown": level.get("score_breakdown", {}),
                    "merged_from": level.get("merged_from", 1)
                })
            
            # Sort by strength score
            key_levels.sort(key=lambda x: x["strength_score"], reverse=True)
            
            # Get state summary
            state_summary = self._state.get_state_summary()
            
            result = {
                "key_levels": key_levels,
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "support_score": support_score,
                "resistance_score": resistance_score,
                "metadata": {
                    "analysis_timestamp": current_time,
                    "total_levels": len(scored_levels),
                    "active_levels": active_count,
                    "inactive_levels": inactive_count,
                    "mtf_confirmed": mtf_confirmed_count,
                    "broken_levels": state_summary['broken_levels_count'],
                    "role_reversals": state_summary['role_reversals_count'],
                    "atr_5m": atr_14,
                    "recalculation_reasons": state_summary['recalculation_reasons'],
                    "symbol": self.symbol
                },
                "top_2_support": [level for level in key_levels if level["type"] == "support" and level["price_level"] < current_price][:2],
                "top_2_resistance": [level for level in key_levels if level["type"] == "resistance" and level["price_level"] > current_price][:2]
            }
            
            # Cache the result
            cache_key = f"sr_analysis_{self.symbol}_{current_price:.0f}"
            # Use CentralizedCache TTL instead of hardcoded value
            from core.services.centralized_cache import get_global_centralized_cache
            cache = get_global_centralized_cache()
            cache.set(cache_key, result)
            
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
            "key_levels": [],
            "strongest_support": 0.0,
            "strongest_resistance": 0.0,
            "support_score": 0.0,
            "resistance_score": 0.0,
            "metadata": {
                "analysis_timestamp": time.time(),
                "error": error_message,
                "total_levels": 0,
                "active_levels": 0,
                "inactive_levels": 0,
                "mtf_confirmed": 0,
                "broken_levels": 0,
                "role_reversals": 0,
                "symbol": self.symbol
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
