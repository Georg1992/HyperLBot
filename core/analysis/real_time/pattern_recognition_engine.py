#!/usr/bin/env python3
"""
Pattern Recognition Engine Module
Identifies important trading patterns for BTC market setups
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

# Singleton pattern implementation
_global_pattern_recognition_engine = None

# Factory function for backward compatibility
def create_pattern_recognition_engine() -> 'PatternRecognitionEngine':
    """
    Factory function to create PatternRecognitionEngine with dependency injection
    
    Returns:
        Configured PatternRecognitionEngine instance
    """
    return PatternRecognitionEngine()

def get_global_pattern_recognition_engine() -> 'PatternRecognitionEngine':
    """Get the global PatternRecognitionEngine singleton instance"""
    global _global_pattern_recognition_engine
    if _global_pattern_recognition_engine is None:
        _global_pattern_recognition_engine = create_pattern_recognition_engine()
    return _global_pattern_recognition_engine

class PatternRecognitionEngine:
    """Recognizes trading patterns for BTC market setups"""
    
    def __init__(self, symbol: str = "BTC"):
        # Trading symbol
        self.symbol = symbol
        
        # Pattern detection parameters
        self.min_pattern_length = 5  # Minimum candles for pattern
        self.max_pattern_length = 50  # Maximum candles for pattern
        self.tolerance = 0.02  # 2% tolerance for pattern matching
        
        # Pattern confidence thresholds
        self.high_confidence = 0.8
        self.medium_confidence = 0.6
        self.low_confidence = 0.4
        
        # Caching to prevent excessive recalculation
        self._last_candle_hash = None
        # Use CentralizedCache TTL instead of hardcoded value
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        # Pattern expiration times (in minutes) for 5m chart
        # Formula: candle_interval (5m) × number_of_candles
        self.pattern_expiration = {
            # Reversal patterns - discard after 4 candles (20 minutes)
            "HEAD_SHOULDERS": 20,
            "INVERSE_HEAD_SHOULDERS": 20,
            "DOUBLE_TOP": 20,
            "DOUBLE_BOTTOM": 20,
            "TREND_CHANGE": 20,
            
            # Triangle patterns - discard after 3 candles (15 minutes)
            "ASCENDING_TRIANGLE": 15,
            "DESCENDING_TRIANGLE": 15,
            "SYMMETRICAL_TRIANGLE": 15,
            
            # Wedge patterns - discard after 3 candles (15 minutes)
            "RISING_WEDGE": 15,
            "FALLING_WEDGE": 15,
            
            # Channel patterns - longer validity (10 candles = 50 minutes)
            "HORIZONTAL_CHANNEL": 50,
            "ASCENDING_CHANNEL": 50,
            "DESCENDING_CHANNEL": 50,
            
            # Continuation patterns - shorter validity (3 candles = 15 minutes)
            "BULLISH_CONTINUATION": 15,
            "BEARISH_CONTINUATION": 15,
            
            # Candlestick patterns - very short validity (3 candles = 15 minutes)
            "BULLISH_ENGULFING": 15,
            "BEARISH_ENGULFING": 15,
            "HAMMER": 15,
            "INVERTED_HAMMER": 15,
            "SHOOTING_STAR": 15,
            "HANGING_MAN": 15,
            "DOJI": 10,
            "DRAGONFLY_DOJI": 10,
            "GRAVESTONE_DOJI": 10,
            "THREE_WHITE_SOLDIERS": 20,
            "THREE_BLACK_CROWS": 20,
        }
        
        
        # Pattern history to track first detection time
        self.pattern_history = {}
        
        logger.info("📊 Pattern Recognition Engine initialized")
        logger.info(f"   ⚡ {len(self.pattern_expiration)} pattern types with expiration times")
        logger.info(f"   🕯️ 9 candlestick patterns supported")
        logger.info(f"   ⏰ Pattern expiration: 10-50 minutes based on pattern type")
    
    def analyze_patterns(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze candles for trading patterns with caching to prevent excessive recalculation
        
        Args:
            candles: List of candle data with OHLC
            
        Returns:
            Dictionary with pattern analysis
        """
        try:
            current_time = time.time()
            
            # Calculate current price from latest candle
            current_price = candles[-1]['close'] if candles else 0
            
            # Check if we can use cached results using CentralizedCache
            cache_key = f"pattern_analysis_{self.symbol}_{current_price:.0f}"
            cached_result = self._cache.get(cache_key)
            if cached_result:
                logger.debug(f"📊 Using cached pattern analysis from CentralizedCache")
                return cached_result
            
            # Check if candle data has changed significantly (stability check)
            current_candle_hash = self._calculate_candle_data_hash(candles)
            if (hasattr(self, '_last_candle_hash') and 
                self._last_candle_hash == current_candle_hash and
                current_time - self._last_analysis_time < 60):  # 1 minute stability
                logger.debug("📊 Candle data unchanged - skipping pattern re-analysis")
                return self._last_analysis_result
            
            if len(candles) < self.min_pattern_length:
                logger.warning(f"⚠️ Insufficient candles for pattern analysis: {len(candles)} < {self.min_pattern_length}")
                raise Exception(f"Insufficient candles for pattern analysis: {len(candles)} < {self.min_pattern_length}")
            
            logger.debug(f"📊 Performing fresh pattern analysis on {len(candles)} candles")
            
            # Extract price data
            prices = self._extract_price_data(candles)
            
            # Detect all patterns
            patterns = {
                "reversal_patterns": self._detect_reversal_patterns(prices),
                "continuation_patterns": self._detect_continuation_patterns(prices),
                "triangle_patterns": self._detect_triangle_patterns(prices),
                "channel_patterns": self._detect_channel_patterns(prices),
                "wedge_patterns": self._detect_wedge_patterns(prices),
                "trend_patterns": self._detect_trend_patterns(prices),
                "candlestick_patterns": self._detect_candlestick_patterns(candles)
            }
            
            # CRITICAL FIX: Calculate pattern birth time from historical data
            patterns = self._calculate_pattern_birth_times(patterns, candles, current_time)
            
            # Track pattern first detection time and add timestamps
            self._track_pattern_timestamps(patterns, current_time)
            
            # Filter out expired patterns
            patterns = self._filter_expired_patterns(patterns, current_time)
            
            # Also clean up expired patterns from history
            self._cleanup_expired_pattern_history(current_time)
            
            # Debug: Log pattern ages
            for pattern_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "UNKNOWN")
                    age_minutes = pattern.get("age_minutes", 0)
                    max_age = self.pattern_expiration.get(pattern_name, 40)
                    logger.info(f"🔍 Pattern {pattern_name}: age={age_minutes:.1f}m, max={max_age}m, valid={age_minutes <= max_age}")
            
            # CRITICAL FIX: Resolve conflicting patterns BEFORE returning to dashboard
            # This ensures only viable patterns are displayed on the chart
            patterns = self._resolve_pattern_conflicts(patterns)
            
            # Calculate overall pattern confidence
            overall_confidence = self._calculate_overall_confidence(patterns)
            
            # Determine market setup
            market_setup = self._determine_market_setup(patterns, overall_confidence)
            
            # Cache the results
            result = {
                "patterns": patterns,
                "overall_confidence": overall_confidence,
                "market_setup": market_setup,
                "pattern_count": sum(len(p) for p in patterns.values()),
                "timestamp": current_time,
                "data_source": "pattern_recognition"
            }
            
            # Cache result using CentralizedCache
            cache_key = f"pattern_analysis_{self.symbol}_{current_price:.0f}"
            self._cache.set(cache_key, result)
            self._last_candle_hash = current_candle_hash
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}")
            raise Exception(f"Pattern analysis failed: {e}")
    
    def _calculate_candle_data_hash(self, candles: List[Dict[str, Any]]) -> str:
        """Calculate hash of candle data to detect changes"""
        try:
            # Create a simple hash based on OHLC data
            hash_data = []
            for candle in candles[-10:]:  # Only use last 10 candles for hash
                hash_data.append((
                    candle.get('open', 0),
                    candle.get('high', 0),
                    candle.get('low', 0),
                    candle.get('close', 0)
                ))
            return str(hash(tuple(hash_data)))
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate candle hash: {e}")
            return str(time.time())  # Fallback to timestamp
    
    def invalidate_cache(self):
        """Invalidate the pattern analysis cache to force fresh calculation"""
        # Clear candle hash to force fresh analysis
        self._last_candle_hash = None
        logger.debug("📊 Pattern analysis cache invalidated")
    
    def _calculate_pattern_birth_times(self, patterns: Dict[str, List[Dict[str, Any]]], candles: List[Dict[str, Any]], current_time: float) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate when patterns were actually "born" in the historical data
        
        Args:
            patterns: Dictionary of detected patterns
            candles: List of candle data with timestamps
            current_time: Current timestamp
            
        Returns:
            Patterns with birth_time and age_minutes calculated from historical data
        """
        try:
            # Get the most recent candle timestamp as reference
            if not candles:
                return patterns
                
            most_recent_candle_time = candles[-1].get('timestamp', current_time)
            
            # Calculate how many candles back each pattern was formed
            for pattern_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "UNKNOWN")
                    
                    # Estimate pattern birth based on pattern type and candle count
                    birth_candles_ago = self._estimate_pattern_birth_candles(pattern_name, pattern)
                    
                    # Calculate birth timestamp
                    if birth_candles_ago > 0 and birth_candles_ago < len(candles):
                        # Get the candle timestamp from birth_candles_ago
                        birth_candle_index = len(candles) - 1 - birth_candles_ago
                        if birth_candle_index >= 0:
                            birth_timestamp = candles[birth_candle_index].get('timestamp', current_time)
                        else:
                            birth_timestamp = candles[0].get('timestamp', current_time)
                    else:
                        # Fallback: use the oldest candle timestamp
                        birth_timestamp = candles[0].get('timestamp', current_time)
                    
                    # Calculate age from birth time
                    age_minutes = (current_time - birth_timestamp) / 60.0
                    
                    # Add birth information to pattern
                    pattern["birth_timestamp"] = birth_timestamp
                    pattern["birth_candles_ago"] = birth_candles_ago
                    pattern["age_minutes"] = age_minutes
                    
                    logger.debug(f"🕐 Pattern {pattern_name}: born {birth_candles_ago} candles ago, age: {age_minutes:.1f}m")
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Pattern birth time calculation failed: {e}")
            return patterns
    
    def _estimate_pattern_birth_candles(self, pattern_name: str, pattern: Dict[str, Any]) -> int:
        """
        Estimate how many candles ago a pattern was born based on pattern characteristics
        
        Args:
            pattern_name: Name of the pattern
            pattern: Pattern data
            
        Returns:
            Number of candles ago the pattern was born
        """
        try:
            # Pattern-specific birth estimation based on typical formation time
            pattern_birth_estimates = {
                # Reversal patterns - typically form over 5-15 candles
                "HEAD_SHOULDERS": 12,
                "INVERSE_HEAD_SHOULDERS": 12,
                "DOUBLE_TOP": 8,
                "DOUBLE_BOTTOM": 8,
                "TREND_CHANGE": 6,
                
                # Triangle patterns - typically form over 8-12 candles
                "ASCENDING_TRIANGLE": 10,
                "DESCENDING_TRIANGLE": 10,
                "SYMMETRIC_TRIANGLE": 10,
                
                # Wedge patterns - typically form over 6-10 candles
                "RISING_WEDGE": 8,
                "FALLING_WEDGE": 8,
                
                # Channel patterns - typically form over 10-20 candles
                "HORIZONTAL_CHANNEL": 15,
                "ASCENDING_CHANNEL": 15,
                "DESCENDING_CHANNEL": 15,
                
                # Continuation patterns - typically form over 3-8 candles
                "BULLISH_CONTINUATION": 5,
                "BEARISH_CONTINUATION": 5,
                
                # Candlestick patterns - typically form over 1-3 candles
                "BULLISH_ENGULFING": 2,
                "BEARISH_ENGULFING": 2,
                "HAMMER": 1,
                "INVERTED_HAMMER": 1,
                "SHOOTING_STAR": 1,
                "THREE_WHITE_SOLDIERS": 3,
                "THREE_BLACK_CROWS": 3,
                "MORNING_DOJI_STAR": 3,
                "EVENING_DOJI_STAR": 3
            }
            
            # Get base estimate
            base_estimate = pattern_birth_estimates.get(pattern_name, 8)
            
            # Adjust based on pattern confidence (higher confidence = more recent formation)
            confidence = pattern.get("confidence", 0.5)
            if confidence > 0.8:
                # High confidence patterns are likely more recent
                base_estimate = max(1, int(base_estimate * 0.7))
            elif confidence < 0.4:
                # Low confidence patterns might be older
                base_estimate = int(base_estimate * 1.3)
            
            # Ensure reasonable bounds
            return max(1, min(base_estimate, 20))
            
        except Exception as e:
            logger.error(f"❌ Pattern birth estimation failed for {pattern_name}: {e}")
            return 8  # Default fallback
    
    def _track_pattern_timestamps(self, patterns: Dict[str, List[Dict[str, Any]]], current_time: float):
        """
        Track when patterns were first detected and add timestamps to pattern data
        
        Args:
            patterns: Dictionary of pattern lists
            current_time: Current timestamp
        """
        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                pattern_name = pattern.get("pattern", "UNKNOWN")
                pattern_key = self._get_pattern_key(pattern)
                
                # Use the calculated birth time from historical data
                birth_timestamp = pattern.get("birth_timestamp", current_time)
                age_minutes = pattern.get("age_minutes", 0)
                
                # If pattern is new, record first detection time using birth timestamp
                if pattern_key not in self.pattern_history:
                    self.pattern_history[pattern_key] = {
                        "first_detected": birth_timestamp,  # Use birth time, not current time
                        "pattern_name": pattern_name,
                        "pattern_type": pattern_type
                    }
                    logger.info(f"🆕 NEW PATTERN DETECTED: {pattern_name} born {age_minutes:.1f}m ago (key: {pattern_key})")
                else:
                    logger.debug(f"🔄 EXISTING PATTERN: {pattern_name} (key: {pattern_key})")
                
                # Add timestamp fields to pattern (use birth time for age calculation)
                original_first_detected = self.pattern_history[pattern_key]["first_detected"]
                pattern["first_detected"] = original_first_detected
                # Age is already calculated from birth time, but ensure it's consistent
                pattern["age_minutes"] = (current_time - original_first_detected) / 60.0
    
    def _filter_expired_patterns(self, patterns: Dict[str, List[Dict[str, Any]]], current_time: float) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter out patterns that have exceeded their expiration time
        
        Args:
            patterns: Dictionary of pattern lists
            current_time: Current timestamp
            
        Returns:
            Filtered dictionary with only valid (non-expired) patterns
        """
        filtered_patterns = {}
        expired_count = 0
        
        for pattern_type, pattern_list in patterns.items():
            valid_patterns = []
            
            for pattern in pattern_list:
                pattern_name = pattern.get("pattern", "UNKNOWN")
                age_minutes = pattern.get("age_minutes", 0)
                max_age = self.pattern_expiration.get(pattern_name, 40)  # Default 40 minutes
                
                if age_minutes <= max_age:
                    # Pattern is still valid
                    valid_patterns.append(pattern)
                    logger.debug(f"⏰ Pattern VALID: {pattern_name} (age: {age_minutes:.1f}m / max: {max_age}m, confidence: {pattern.get('confidence', 0):.1%})")
                else:
                    # Pattern expired - remove from history and discard
                    pattern_key = self._get_pattern_key(pattern)
                    if pattern_key in self.pattern_history:
                        del self.pattern_history[pattern_key]
                    
                    expired_count += 1
                    logger.info(f"⏰ Pattern EXPIRED: {pattern_name} (age: {age_minutes:.1f}m > max: {max_age}m) - DISCARDED")
            
            filtered_patterns[pattern_type] = valid_patterns
        
        if expired_count > 0:
            logger.info(f"🧹 Cleaned up {expired_count} expired pattern(s)")
        
        return filtered_patterns
    
    def _cleanup_expired_pattern_history(self, current_time: float):
        """Clean up expired patterns from pattern_history"""
        try:
            expired_keys = []
            for pattern_key, history_entry in self.pattern_history.items():
                pattern_name = history_entry.get("pattern_name", "UNKNOWN")
                first_detected = history_entry.get("first_detected", current_time)
                age_minutes = (current_time - first_detected) / 60.0
                max_age = self.pattern_expiration.get(pattern_name, 40)
                
                if age_minutes > max_age:
                    expired_keys.append(pattern_key)
            
            for key in expired_keys:
                del self.pattern_history[key]
            
            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired pattern(s) from history")
        except Exception as e:
            logger.error(f"❌ Failed to cleanup pattern history: {e}")
    
    def _get_pattern_key(self, pattern: Dict[str, Any]) -> str:
        """
        Generate a unique key for a pattern based on its characteristics
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Unique string key for the pattern
        """
        pattern_name = pattern.get("pattern", "UNKNOWN")
        
        # Use price levels instead of candle indices for consistent keys across time
        # This ensures patterns maintain their identity even as new candles arrive
        pattern_high = pattern.get("pattern_high", 0)
        pattern_low = pattern.get("pattern_low", 0)
        
        # For patterns with specific price points (H&S, Double Top/Bottom)
        if "head" in pattern:
            # Head and shoulders patterns - use rounded head price for stability
            head_price = pattern.get("head", 0)
            # Round to nearest 10 to handle minor price fluctuations
            rounded_head = int(round(head_price / 10) * 10)
            return f"{pattern_name}_{rounded_head}"
        elif "shoulders" in pattern:
            # Include shoulders for more specific identification
            shoulders = pattern.get("shoulders", [])
            # Round shoulder prices to nearest 10 for stability
            rounded_shoulders = [int(round(s / 10) * 10) for s in shoulders]
            shoulder_prices = "_".join([str(s) for s in rounded_shoulders])
            return f"{pattern_name}_{shoulder_prices}"
        else:
            # Generic key based on pattern name and price levels
            return f"{pattern_name}_{int(pattern_high)}_{int(pattern_low)}"
    
    def _extract_price_data(self, candles: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Extract price data from candles"""
        return {
            "highs": [float(c.get("high", 0)) for c in candles],
            "lows": [float(c.get("low", 0)) for c in candles],
            "opens": [float(c.get("open", 0)) for c in candles],
            "closes": [float(c.get("close", 0)) for c in candles],
            "volumes": [float(c.get("volume", 0)) for c in candles]
        }
    
    def _detect_reversal_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect reversal patterns"""
        patterns = []
        
        # Double Top
        double_top = self._detect_double_top(prices)
        if double_top:
            patterns.append(double_top)
        
        # Double Bottom
        double_bottom = self._detect_double_bottom(prices)
        if double_bottom:
            patterns.append(double_bottom)
        
        # Head & Shoulders
        head_shoulders = self._detect_head_shoulders(prices)
        if head_shoulders:
            patterns.append(head_shoulders)
        
        # Inverse Head & Shoulders
        inverse_hs = self._detect_inverse_head_shoulders(prices)
        if inverse_hs:
            patterns.append(inverse_hs)
        
        return patterns
    
    def _detect_continuation_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect continuation patterns"""
        patterns = []
        
        # Bullish Continuation
        bullish_cont = self._detect_bullish_continuation(prices)
        if bullish_cont:
            patterns.append(bullish_cont)
        
        # Bearish Continuation
        bearish_cont = self._detect_bearish_continuation(prices)
        if bearish_cont:
            patterns.append(bearish_cont)
        
        return patterns
    
    def _detect_triangle_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect triangle patterns with proper conflict resolution"""
        patterns = []
        
        # Detect all triangle types
        asc_triangle = self._detect_ascending_triangle(prices)
        desc_triangle = self._detect_descending_triangle(prices)
        sym_triangle = self._detect_symmetrical_triangle(prices)
        
        # Get all valid triangle patterns
        triangle_patterns = []
        if asc_triangle:
            triangle_patterns.append(asc_triangle)
        if desc_triangle:
            triangle_patterns.append(desc_triangle)
        if sym_triangle:
            triangle_patterns.append(sym_triangle)
        
        # Only return ONE triangle pattern - the one with highest confidence
        if triangle_patterns:
            # Sort by confidence (highest first)
            triangle_patterns.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            best_pattern = triangle_patterns[0]
            
            # Only add if confidence is significantly higher than others
            if len(triangle_patterns) > 1:
                second_best = triangle_patterns[1].get("confidence", 0)
                if best_pattern.get("confidence", 0) > second_best + 0.1:  # 10% difference
                    patterns.append(best_pattern)
                # If confidence is too close, don't show any triangle
            else:
                patterns.append(best_pattern)
        
        return patterns
    
    def _detect_channel_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect channel patterns"""
        patterns = []
        
        # Horizontal Channel
        horiz_channel = self._detect_horizontal_channel(prices)
        if horiz_channel:
            patterns.append(horiz_channel)
        
        # Ascending Channel
        asc_channel = self._detect_ascending_channel(prices)
        if asc_channel:
            patterns.append(asc_channel)
        
        # Descending Channel
        desc_channel = self._detect_descending_channel(prices)
        if desc_channel:
            patterns.append(desc_channel)
        
        return patterns
    
    def _detect_wedge_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect wedge patterns"""
        patterns = []
        
        # Rising Wedge
        rising_wedge = self._detect_rising_wedge(prices)
        if rising_wedge:
            patterns.append(rising_wedge)
        
        # Falling Wedge
        falling_wedge = self._detect_falling_wedge(prices)
        if falling_wedge:
            patterns.append(falling_wedge)
        
        return patterns
    
    def _detect_trend_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect trend patterns"""
        patterns = []
        
        # Trend Change Detection
        trend_change = self._detect_trend_change(prices)
        if trend_change:
            patterns.append(trend_change)
        
        return patterns
    
    def _detect_candlestick_patterns(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect candlestick patterns (single or multi-candle formations)"""
        patterns = []
        
        if len(candles) < 3:
            return patterns
        
        # Check last 3 candles for patterns
        recent_candles = candles[-3:]
        
        # Engulfing patterns (2 candles)
        if len(recent_candles) >= 2:
            engulfing = self._detect_engulfing(recent_candles[-2:])
            if engulfing:
                patterns.append(engulfing)
        
        # Hammer, Shooting Star, Doji (single candle)
        single_pattern = self._detect_single_candlestick(recent_candles[-1])
        if single_pattern:
            patterns.append(single_pattern)
        
        # Three Soldiers/Crows (3 candles)
        if len(recent_candles) >= 3:
            three_pattern = self._detect_three_candles(recent_candles)
            if three_pattern:
                patterns.append(three_pattern)
        
        return patterns
    
    def _detect_engulfing(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect bullish or bearish engulfing pattern"""
        if len(candles) < 2:
            return None
        
        prev_candle = candles[0]
        curr_candle = candles[1]
        
        prev_open = float(prev_candle.get("open", 0))
        prev_close = float(prev_candle.get("close", 0))
        curr_open = float(curr_candle.get("open", 0))
        curr_close = float(curr_candle.get("close", 0))
        
        if not all([prev_open, prev_close, curr_open, curr_close]):
            return None
        
        prev_body = abs(prev_close - prev_open)
        curr_body = abs(curr_close - curr_open)
        
        # Require current candle to have significant body (not doji)
        if curr_body < prev_body * 0.5:
            return None
        
        # Bullish Engulfing: prev bearish, curr bullish, curr engulfs prev
        if prev_close < prev_open and curr_close > curr_open:
            if curr_open <= prev_close and curr_close >= prev_open:
                confidence = min(0.9, (curr_body / prev_body) * 0.5)
                return {
                    "pattern": "BULLISH_ENGULFING",
                    "type": "REVERSAL",
                    "direction": "BULLISH",
                    "confidence": confidence,
                    "indices": [len(candles) - 2, len(candles) - 1],
                    "start_candle_index": len(candles) - 2,
                    "end_candle_index": len(candles) - 1,
                    "pattern_high": max(curr_open, curr_close),
                    "pattern_low": min(prev_open, prev_close),
                }
        
        # Bearish Engulfing: prev bullish, curr bearish, curr engulfs prev
        elif prev_close > prev_open and curr_close < curr_open:
            if curr_open >= prev_close and curr_close <= prev_open:
                confidence = min(0.9, (curr_body / prev_body) * 0.5)
                return {
                    "pattern": "BEARISH_ENGULFING",
                    "type": "REVERSAL",
                    "direction": "BEARISH",
                    "confidence": confidence,
                    "indices": [len(candles) - 2, len(candles) - 1],
                    "start_candle_index": len(candles) - 2,
                    "end_candle_index": len(candles) - 1,
                    "pattern_high": max(prev_open, prev_close),
                    "pattern_low": min(curr_open, curr_close),
                }
        
        return None
    
    def _detect_single_candlestick(self, candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect single candlestick patterns (Hammer, Shooting Star, Doji)"""
        open_price = float(candle.get("open", 0))
        close_price = float(candle.get("close", 0))
        high_price = float(candle.get("high", 0))
        low_price = float(candle.get("low", 0))
        
        if not all([open_price, close_price, high_price, low_price]):
            return None
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return None
        
        body_ratio = body / total_range
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price
        
        # DOJI: Very small body (< 10% of range)
        if body_ratio < 0.1:
            if lower_shadow > body * 5:
                # Dragonfly Doji: long lower shadow
                return {
                    "pattern": "DRAGONFLY_DOJI",
                    "type": "REVERSAL",
                    "direction": "BULLISH",
                    "confidence": 0.7,
                    "indices": [0],
                    "start_candle_index": 0,
                    "end_candle_index": 0,
                    "pattern_high": high_price,
                    "pattern_low": low_price,
                }
            elif upper_shadow > body * 5:
                # Gravestone Doji: long upper shadow
                return {
                    "pattern": "GRAVESTONE_DOJI",
                    "type": "REVERSAL",
                    "direction": "BEARISH",
                    "confidence": 0.7,
                    "indices": [0],
                    "start_candle_index": 0,
                    "end_candle_index": 0,
                    "pattern_high": high_price,
                    "pattern_low": low_price,
                }
            else:
                # Standard Doji: indecision
                return {
                    "pattern": "DOJI",
                    "type": "REVERSAL",
                    "direction": "NEUTRAL",
                    "confidence": 0.6,
                    "indices": [0],
                    "start_candle_index": 0,
                    "end_candle_index": 0,
                    "pattern_high": high_price,
                    "pattern_low": low_price,
                }
        
        # HAMMER / INVERTED HAMMER: Small body (< 30%), long shadow (> 2x body)
        elif body_ratio < 0.3:
            if lower_shadow > body * 2 and upper_shadow < body:
                # Hammer: long lower shadow, bullish reversal
                is_bullish = close_price > open_price
                return {
                    "pattern": "HAMMER",
                    "type": "REVERSAL",
                    "direction": "BULLISH",
                    "confidence": 0.8 if is_bullish else 0.7,
                    "indices": [0],
                    "start_candle_index": 0,
                    "end_candle_index": 0,
                    "pattern_high": high_price,
                    "pattern_low": low_price,
                }
            elif upper_shadow > body * 2 and lower_shadow < body:
                # Could be Inverted Hammer (bullish) or Shooting Star (bearish)
                # Inverted Hammer appears at bottom, Shooting Star at top
                # We'll use candle color as proxy
                is_bullish = close_price > open_price
                if is_bullish:
                    return {
                        "pattern": "INVERTED_HAMMER",
                        "type": "REVERSAL",
                        "direction": "BULLISH",
                        "confidence": 0.75,
                        "indices": [0],
                        "start_candle_index": 0,
                        "end_candle_index": 0,
                        "pattern_high": high_price,
                        "pattern_low": low_price,
                    }
                else:
                    return {
                        "pattern": "SHOOTING_STAR",
                        "type": "REVERSAL",
                        "direction": "BEARISH",
                        "confidence": 0.8,
                        "indices": [0],
                        "start_candle_index": 0,
                        "end_candle_index": 0,
                        "pattern_high": high_price,
                        "pattern_low": low_price,
                    }
        
        return None
    
    def _detect_three_candles(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect Three White Soldiers or Three Black Crows"""
        if len(candles) < 3:
            return None
        
        # Check if all three candles are bullish (White Soldiers)
        all_bullish = True
        all_bearish = True
        
        closes = []
        opens = []
        
        for candle in candles:
            open_price = float(candle.get("open", 0))
            close_price = float(candle.get("close", 0))
            
            if not open_price or not close_price:
                return None
            
            opens.append(open_price)
            closes.append(close_price)
            
            if close_price <= open_price:
                all_bullish = False
            if close_price >= open_price:
                all_bearish = False
        
        # Three White Soldiers: 3 consecutive bullish candles with higher closes
        if all_bullish:
            if closes[1] > closes[0] and closes[2] > closes[1]:
                confidence = 0.85
                return {
                    "pattern": "THREE_WHITE_SOLDIERS",
                    "type": "CONTINUATION",
                    "direction": "BULLISH",
                    "confidence": confidence,
                    "indices": [0, 1, 2],
                    "start_candle_index": 0,
                    "end_candle_index": 2,
                    "pattern_high": max(closes),
                    "pattern_low": min(opens),
                }
        
        # Three Black Crows: 3 consecutive bearish candles with lower closes
        elif all_bearish:
            if closes[1] < closes[0] and closes[2] < closes[1]:
                confidence = 0.85
                return {
                    "pattern": "THREE_BLACK_CROWS",
                    "type": "CONTINUATION",
                    "direction": "BEARISH",
                    "confidence": confidence,
                    "indices": [0, 1, 2],
                    "start_candle_index": 0,
                    "end_candle_index": 2,
                    "pattern_high": max(opens),
                    "pattern_low": min(closes),
                }
        
        return None
    
    def _detect_double_top(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect double top pattern"""
        try:
            highs = prices["highs"]
            if len(highs) < 10:
                return None
            
            # Find peaks
            peaks = self._find_peaks(highs)
            if len(peaks) < 2:
                return None
            
            # Look for two similar peaks
            for i in range(len(peaks) - 1):
                for j in range(i + 1, len(peaks)):
                    peak1_idx, peak1_val = peaks[i]
                    peak2_idx, peak2_val = peaks[j]
                    
                    # Check if peaks are similar in height
                    if abs(peak1_val - peak2_val) / peak1_val < self.tolerance:
                        # Check if there's a valley between them
                        valley_idx = self._find_valley_between(highs, peak1_idx, peak2_idx)
                        if valley_idx:
                            valley_val = highs[valley_idx]
                            # Valley should be significantly lower
                            if (peak1_val - valley_val) / peak1_val > 0.02:  # 2% minimum
                                confidence = self._calculate_pattern_confidence(highs, peak1_idx, peak2_idx, valley_idx)
                                return {
                                    "pattern": "DOUBLE_TOP",
                                    "type": "REVERSAL",
                                    "direction": "BEARISH",
                                    "confidence": confidence,
                                    "peaks": [peak1_val, peak2_val],
                                    "valley": valley_val,
                                    "indices": [peak1_idx, valley_idx, peak2_idx],
                                    "start_candle_index": min(peak1_idx, peak2_idx),
                                    "end_candle_index": max(peak1_idx, peak2_idx),
                                    "pattern_high": max(peak1_val, peak2_val),
                                    "pattern_low": valley_val,
                                    "description": "Double top reversal pattern - bearish signal"
                                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Double top detection failed: {e}")
            return None
    
    def _detect_double_bottom(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect double bottom pattern"""
        try:
            lows = prices["lows"]
            if len(lows) < 10:
                return None
            
            # Find valleys
            valleys = self._find_valleys(lows)
            if len(valleys) < 2:
                return None
            
            # Look for two similar valleys
            for i in range(len(valleys) - 1):
                for j in range(i + 1, len(valleys)):
                    valley1_idx, valley1_val = valleys[i]
                    valley2_idx, valley2_val = valleys[j]
                    
                    # Check if valleys are similar in depth
                    if abs(valley1_val - valley2_val) / valley1_val < self.tolerance:
                        # Check if there's a peak between them
                        peak_idx = self._find_peak_between(lows, valley1_idx, valley2_idx)
                        if peak_idx:
                            peak_val = lows[peak_idx]
                            # Peak should be significantly higher
                            if (peak_val - valley1_val) / valley1_val > 0.02:  # 2% minimum
                                confidence = self._calculate_pattern_confidence(lows, valley1_idx, valley2_idx, peak_idx)
                                return {
                                    "pattern": "DOUBLE_BOTTOM",
                                    "type": "REVERSAL",
                                    "direction": "BULLISH",
                                    "confidence": confidence,
                                    "valleys": [valley1_val, valley2_val],
                                    "peak": peak_val,
                                    "indices": [valley1_idx, peak_idx, valley2_idx],
                                    "start_candle_index": min(valley1_idx, valley2_idx),
                                    "end_candle_index": max(valley1_idx, valley2_idx),
                                    "pattern_high": peak_val,
                                    "pattern_low": min(valley1_val, valley2_val),
                                    "description": "Double bottom reversal pattern - bullish signal"
                                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Double bottom detection failed: {e}")
            return None
    
    def _detect_head_shoulders(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect head and shoulders pattern"""
        try:
            highs = prices["highs"]
            if len(highs) < 15:
                return None
            
            # Find peaks
            peaks = self._find_peaks(highs)
            if len(peaks) < 3:
                return None
            
            # Look for three peaks: left shoulder, head, right shoulder
            for i in range(len(peaks) - 2):
                left_shoulder = peaks[i]
                head = peaks[i + 1]
                right_shoulder = peaks[i + 2]
                
                # Head should be higher than shoulders
                if (head[1] > left_shoulder[1] and 
                    head[1] > right_shoulder[1] and
                    abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1] < self.tolerance):
                    
                    confidence = self._calculate_hs_confidence(highs, left_shoulder, head, right_shoulder)
                    return {
                        "pattern": "HEAD_SHOULDERS",
                        "type": "REVERSAL",
                        "direction": "BEARISH",
                        "confidence": confidence,
                        "head": head[1],
                        "shoulders": [left_shoulder[1], right_shoulder[1]],
                        "indices": [left_shoulder[0], head[0], right_shoulder[0]],
                        "start_candle_index": left_shoulder[0],
                        "end_candle_index": right_shoulder[0],
                        "pattern_high": head[1],
                        "pattern_low": min(left_shoulder[1], right_shoulder[1]),
                        "description": "Head and shoulders reversal pattern - bearish signal"
                    }
            return None
            
        except Exception as e:
            logger.error(f"❌ Head and shoulders detection failed: {e}")
            return None
    
    def _detect_inverse_head_shoulders(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect inverse head and shoulders pattern"""
        try:
            lows = prices["lows"]
            if len(lows) < 15:
                return None
            
            # Find valleys
            valleys = self._find_valleys(lows)
            if len(valleys) < 3:
                return None
            
            # Look for three valleys: left shoulder, head, right shoulder
            for i in range(len(valleys) - 2):
                left_shoulder = valleys[i]
                head = valleys[i + 1]
                right_shoulder = valleys[i + 2]
                
                # Head should be lower than shoulders
                if (head[1] < left_shoulder[1] and 
                    head[1] < right_shoulder[1] and
                    abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1] < self.tolerance):
                    
                    confidence = self._calculate_hs_confidence(lows, left_shoulder, head, right_shoulder)
                    return {
                        "pattern": "INVERSE_HEAD_SHOULDERS",
                        "type": "REVERSAL",
                        "direction": "BULLISH",
                        "confidence": confidence,
                        "head": head[1],
                        "shoulders": [left_shoulder[1], right_shoulder[1]],
                        "indices": [left_shoulder[0], head[0], right_shoulder[0]],
                        "start_candle_index": left_shoulder[0],
                        "end_candle_index": right_shoulder[0],
                        "pattern_high": max(left_shoulder[1], right_shoulder[1]),
                        "pattern_low": head[1],
                        "description": "Inverse head and shoulders reversal pattern - bullish signal"
                    }
            return None
            
        except Exception as e:
            logger.error(f"❌ Inverse head and shoulders detection failed: {e}")
            return None
    
    def _detect_ascending_triangle(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect ascending triangle pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 10:
                return None
            
            # Look for flat resistance and rising support
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Check for flat resistance
            resistance_level = np.mean(recent_highs)
            resistance_variance = np.var(recent_highs) / resistance_level
            
            if resistance_variance < 0.01:  # Low variance = flat resistance
                # Check for rising support
                support_slope = self._calculate_slope(recent_lows)
                if support_slope > 0:  # Rising support
                    confidence = min(0.9, 1.0 - resistance_variance * 10)
                    return {
                        "pattern": "ASCENDING_TRIANGLE",
                        "type": "CONTINUATION",
                        "direction": "BULLISH",
                        "confidence": confidence,
                        "resistance_level": resistance_level,
                        "support_slope": support_slope,
                        "start_candle_index": len(highs) - 10,
                        "end_candle_index": len(highs) - 1,
                        "pattern_high": resistance_level,
                        "pattern_low": min(recent_lows),
                        "description": "Ascending triangle - bullish continuation pattern"
                    }
            return None
            
        except Exception as e:
            logger.error(f"❌ Ascending triangle detection failed: {e}")
            return None
    
    def _detect_descending_triangle(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect descending triangle pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 10:
                return None
            
            # Look for flat support and falling resistance
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Check for flat support
            support_level = np.mean(recent_lows)
            support_variance = np.var(recent_lows) / support_level
            
            if support_variance < 0.01:  # Low variance = flat support
                # Check for falling resistance
                resistance_slope = self._calculate_slope(recent_highs)
                if resistance_slope < 0:  # Falling resistance
                    confidence = min(0.9, 1.0 - support_variance * 10)
                    return {
                        "pattern": "DESCENDING_TRIANGLE",
                        "type": "CONTINUATION",
                        "direction": "BEARISH",
                        "confidence": confidence,
                        "support_level": support_level,
                        "resistance_slope": resistance_slope,
                        "description": "Descending triangle - bearish continuation pattern"
                    }
            return None
            
        except Exception as e:
            logger.error(f"❌ Descending triangle detection failed: {e}")
            return None
    
    def _detect_symmetrical_triangle(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect symmetrical triangle pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 10:
                return None
            
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Check for converging trend lines
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Highs should be falling, lows should be rising (converging)
            if high_slope < 0 and low_slope > 0:
                convergence_rate = abs(high_slope) + abs(low_slope)
                confidence = min(0.8, convergence_rate * 10)
                
                # Calculate pattern bounds for chart visualization (relative to last 20 candles shown on chart)
                # Chart shows last 20 candles, so indices should be relative to that window
                pattern_start_idx = max(0, 20 - 10)  # Start 10 candles from the end of visible window
                pattern_end_idx = 19  # End at the last visible candle (index 19 for 20 candles)
                pattern_high = max(recent_highs[-10:]) if len(recent_highs) >= 10 else max(recent_highs)
                pattern_low = min(recent_lows[-10:]) if len(recent_lows) >= 10 else min(recent_lows)
                
                return {
                    "pattern": "SYMMETRICAL_TRIANGLE",
                    "type": "CONTINUATION",
                    "direction": "NEUTRAL",
                    "confidence": confidence,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "convergence_rate": convergence_rate,
                    "start_candle_index": pattern_start_idx,
                    "end_candle_index": pattern_end_idx,
                    "pattern_high": pattern_high,
                    "pattern_low": pattern_low,
                    "description": "Symmetrical triangle - neutral continuation pattern"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Symmetrical triangle detection failed: {e}")
            return None
    
    def _detect_horizontal_channel(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect horizontal channel pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 15:
                return None
            
            recent_highs = highs[-15:]
            recent_lows = lows[-15:]
            
            # Check for parallel horizontal lines
            high_variance = np.var(recent_highs) / np.mean(recent_highs)
            low_variance = np.var(recent_lows) / np.mean(recent_lows)
            
            if high_variance < 0.02 and low_variance < 0.02:  # Low variance = horizontal
                channel_width = np.mean(recent_highs) - np.mean(recent_lows)
                confidence = min(0.9, 1.0 - (high_variance + low_variance) * 10)
                return {
                    "pattern": "HORIZONTAL_CHANNEL",
                    "type": "CONTINUATION",
                    "direction": "NEUTRAL",
                    "confidence": confidence,
                    "resistance_level": np.mean(recent_highs),
                    "support_level": np.mean(recent_lows),
                    "channel_width": channel_width,
                    "start_candle_index": len(highs) - 10,
                    "end_candle_index": len(highs) - 1,
                    "pattern_high": np.mean(recent_highs),
                    "pattern_low": np.mean(recent_lows),
                    "description": "Horizontal channel - neutral continuation pattern"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Horizontal channel detection failed: {e}")
            return None
    
    def _detect_ascending_channel(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect ascending channel pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 15:
                return None
            
            recent_highs = highs[-15:]
            recent_lows = lows[-15:]
            
            # Check for parallel upward-sloping lines
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            if high_slope > 0 and low_slope > 0:  # Both rising
                slope_diff = abs(high_slope - low_slope)
                if slope_diff < 0.01:  # Parallel lines
                    confidence = min(0.9, 1.0 - slope_diff * 100)
                    return {
                        "pattern": "ASCENDING_CHANNEL",
                        "type": "CONTINUATION",
                        "direction": "BULLISH",
                        "confidence": confidence,
                        "high_slope": high_slope,
                        "low_slope": low_slope,
                        "description": "Ascending channel - bullish continuation pattern"
                    }
            return None
            
        except Exception as e:
            logger.error(f"❌ Ascending channel detection failed: {e}")
            return None
    
    def _detect_descending_channel(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect descending channel pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 15:
                return None
            
            recent_highs = highs[-15:]
            recent_lows = lows[-15:]
            
            # Check for parallel downward-sloping lines
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            if high_slope < 0 and low_slope < 0:  # Both falling
                slope_diff = abs(high_slope - low_slope)
                if slope_diff < 0.01:  # Parallel lines
                    confidence = min(0.9, 1.0 - slope_diff * 100)
                    return {
                        "pattern": "DESCENDING_CHANNEL",
                        "type": "CONTINUATION",
                        "direction": "BEARISH",
                        "confidence": confidence,
                        "high_slope": high_slope,
                        "low_slope": low_slope,
                        "description": "Descending channel - bearish continuation pattern"
                    }
            return None
            
        except Exception as e:
            logger.error(f"❌ Descending channel detection failed: {e}")
            return None
    
    def _detect_rising_wedge(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect rising wedge pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 15:
                return None
            
            recent_highs = highs[-15:]
            recent_lows = lows[-15:]
            
            # Check for converging upward-sloping lines
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            if high_slope > 0 and low_slope > 0 and high_slope > low_slope:  # Converging upward
                convergence_rate = high_slope - low_slope
                confidence = min(0.8, convergence_rate * 20)
                
                # Calculate pattern bounds for chart visualization (relative to last 20 candles shown on chart)
                # Chart shows last 20 candles, so indices should be relative to that window
                pattern_start_idx = max(0, 20 - 15)  # Start 15 candles from the end of visible window
                pattern_end_idx = 19  # End at the last visible candle (index 19 for 20 candles)
                pattern_high = max(recent_highs[-15:]) if len(recent_highs) >= 15 else max(recent_highs)
                pattern_low = min(recent_lows[-15:]) if len(recent_lows) >= 15 else min(recent_lows)
                
                return {
                    "pattern": "RISING_WEDGE",
                    "type": "REVERSAL",
                    "direction": "BEARISH",
                    "confidence": confidence,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "convergence_rate": convergence_rate,
                    "start_candle_index": pattern_start_idx,
                    "end_candle_index": pattern_end_idx,
                    "pattern_high": pattern_high,
                    "pattern_low": pattern_low,
                    "description": "Rising wedge - bearish reversal pattern"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Rising wedge detection failed: {e}")
            return None
    
    def _detect_falling_wedge(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect falling wedge pattern"""
        try:
            highs = prices["highs"]
            lows = prices["lows"]
            if len(highs) < 15:
                return None
            
            recent_highs = highs[-15:]
            recent_lows = lows[-15:]
            
            # Check for converging downward-sloping lines
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            if high_slope < 0 and low_slope < 0 and high_slope < low_slope:  # Converging downward
                convergence_rate = low_slope - high_slope
                confidence = min(0.8, convergence_rate * 20)
                
                # Calculate pattern boundaries for stable key generation
                pattern_high = max(recent_highs)
                pattern_low = min(recent_lows)
                
                return {
                    "pattern": "FALLING_WEDGE",
                    "type": "REVERSAL",
                    "direction": "BULLISH",
                    "confidence": confidence,
                    "pattern_high": pattern_high,
                    "pattern_low": pattern_low,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "convergence_rate": convergence_rate,
                    "description": "Falling wedge - bullish reversal pattern"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Falling wedge detection failed: {e}")
            return None
    
    def _detect_bullish_continuation(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect bullish trend continuation"""
        try:
            closes = prices["closes"]
            if len(closes) < 10:
                return None
            
            # Check for higher highs and higher lows
            recent_closes = closes[-10:]
            higher_highs = sum(1 for i in range(1, len(recent_closes)) 
                             if recent_closes[i] > recent_closes[i-1])
            higher_lows = sum(1 for i in range(1, len(recent_closes)) 
                            if recent_closes[i] > recent_closes[i-1])
            
            if higher_highs >= 6 and higher_lows >= 6:  # Strong uptrend
                confidence = min(0.9, (higher_highs + higher_lows) / 20)
                return {
                    "pattern": "BULLISH_CONTINUATION",
                    "type": "CONTINUATION",
                    "direction": "BULLISH",
                    "confidence": confidence,
                    "higher_highs": higher_highs,
                    "higher_lows": higher_lows,
                    "start_candle_index": len(closes) - 10,
                    "end_candle_index": len(closes) - 1,
                    "pattern_high": max(recent_closes),
                    "pattern_low": min(recent_closes),
                    "description": "Bullish trend continuation pattern"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Bullish continuation detection failed: {e}")
            return None
    
    def _detect_bearish_continuation(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect bearish trend continuation"""
        try:
            closes = prices["closes"]
            if len(closes) < 10:
                return None
            
            # Check for lower highs and lower lows
            recent_closes = closes[-10:]
            lower_highs = sum(1 for i in range(1, len(recent_closes)) 
                            if recent_closes[i] < recent_closes[i-1])
            lower_lows = sum(1 for i in range(1, len(recent_closes)) 
                           if recent_closes[i] < recent_closes[i-1])
            
            if lower_highs >= 6 and lower_lows >= 6:  # Strong downtrend
                confidence = min(0.9, (lower_highs + lower_lows) / 20)
                return {
                    "pattern": "BEARISH_CONTINUATION",
                    "type": "CONTINUATION",
                    "direction": "BEARISH",
                    "confidence": confidence,
                    "lower_highs": lower_highs,
                    "lower_lows": lower_lows,
                    "description": "Bearish trend continuation pattern"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Bearish continuation detection failed: {e}")
            return None
    
    def _detect_trend_change(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect trend change pattern"""
        try:
            closes = prices["closes"]
            if len(closes) < 20:
                return None
            
            # Compare first half vs second half
            mid_point = len(closes) // 2
            first_half = closes[:mid_point]
            second_half = closes[mid_point:]
            
            first_slope = self._calculate_slope(first_half)
            second_slope = self._calculate_slope(second_half)
            
            # Check for trend reversal
            if (first_slope > 0.01 and second_slope < -0.01):  # Uptrend to downtrend
                confidence = min(0.8, abs(first_slope - second_slope) * 10)
                return {
                    "pattern": "TREND_CHANGE",
                    "type": "REVERSAL",
                    "direction": "BEARISH",
                    "confidence": confidence,
                    "first_slope": first_slope,
                    "second_slope": second_slope,
                    "description": "Trend change from uptrend to downtrend"
                }
            elif (first_slope < -0.01 and second_slope > 0.01):  # Downtrend to uptrend
                confidence = min(0.8, abs(first_slope - second_slope) * 10)
                return {
                    "pattern": "TREND_CHANGE",
                    "type": "REVERSAL",
                    "direction": "BULLISH",
                    "confidence": confidence,
                    "first_slope": first_slope,
                    "second_slope": second_slope,
                    "description": "Trend change from downtrend to uptrend"
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Trend change detection failed: {e}")
            return None
    
    def _find_peaks(self, data: List[float]) -> List[Tuple[int, float]]:
        """Find peaks in data"""
        peaks = []
        for i in range(1, len(data) - 1):
            if data[i] > data[i-1] and data[i] > data[i+1]:
                peaks.append((i, data[i]))
        return peaks
    
    def _find_valleys(self, data: List[float]) -> List[Tuple[int, float]]:
        """Find valleys in data"""
        valleys = []
        for i in range(1, len(data) - 1):
            if data[i] < data[i-1] and data[i] < data[i+1]:
                valleys.append((i, data[i]))
        return valleys
    
    def _find_valley_between(self, data: List[float], start: int, end: int) -> Optional[int]:
        """Find valley between two indices"""
        if start >= end:
            return None
        valley_idx = start + 1
        valley_val = data[valley_idx]
        for i in range(start + 1, end):
            if data[i] < valley_val:
                valley_val = data[i]
                valley_idx = i
        return valley_idx if valley_val < data[start] and valley_val < data[end] else None
    
    def _find_peak_between(self, data: List[float], start: int, end: int) -> Optional[int]:
        """Find peak between two indices"""
        if start >= end:
            return None
        peak_idx = start + 1
        peak_val = data[peak_idx]
        for i in range(start + 1, end):
            if data[i] > peak_val:
                peak_val = data[i]
                peak_idx = i
        return peak_idx if peak_val > data[start] and peak_val > data[end] else None
    
    def _calculate_slope(self, data: List[float]) -> float:
        """Calculate slope of data"""
        if len(data) < 2:
            return 0.0
        x = list(range(len(data)))
        return np.polyfit(x, data, 1)[0]
    
    def _calculate_pattern_confidence(self, data: List[float], *indices: int) -> float:
        """Calculate confidence for pattern"""
        try:
            if len(indices) < 2:
                return 0.5
            
            # Base confidence on pattern symmetry and clarity
            values = [data[i] for i in indices]
            variance = np.var(values) / np.mean(values)
            return max(0.3, min(0.9, 1.0 - variance * 5))
            
        except Exception:
            return 0.5
    
    def _calculate_hs_confidence(self, data: List[float], left: Tuple[int, float], 
                                head: Tuple[int, float], right: Tuple[int, float]) -> float:
        """Calculate confidence for head and shoulders pattern"""
        try:
            # Check symmetry of shoulders
            shoulder_diff = abs(left[1] - right[1]) / left[1]
            head_height = (head[1] - left[1]) / left[1]
            
            # Higher confidence for more symmetric shoulders and prominent head
            symmetry_score = 1.0 - shoulder_diff
            prominence_score = min(1.0, head_height * 2)
            
            return max(0.3, min(0.9, (symmetry_score + prominence_score) / 2))
            
        except Exception:
            return 0.5
    
    def _calculate_overall_confidence(self, patterns: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate overall pattern confidence"""
        try:
            all_patterns = []
            for pattern_list in patterns.values():
                all_patterns.extend(pattern_list)
            
            if not all_patterns:
                return 0.0
            
            # Weight by confidence and pattern type
            total_weight = 0
            weighted_confidence = 0
            
            for pattern in all_patterns:
                confidence = pattern.get("confidence", 0.5)
                pattern_type = pattern.get("type", "CONTINUATION")
                
                # Weight reversal patterns higher
                weight = 1.5 if pattern_type == "REVERSAL" else 1.0
                
                weighted_confidence += confidence * weight
                total_weight += weight
            
            return weighted_confidence / total_weight if total_weight > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _resolve_pattern_conflicts(self, patterns: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Resolve conflicting patterns by prioritizing the strongest/most recent"""
        try:
            resolved_patterns = {}
            
            for pattern_type, pattern_list in patterns.items():
                if not pattern_list:
                    resolved_patterns[pattern_type] = []
                    continue
                
                # Group patterns by conflicting types
                conflicting_groups = {
                    "HEAD_SHOULDERS": [],
                    "INVERSE_HEAD_SHOULDERS": [],
                    "DOUBLE_TOP": [],
                    "DOUBLE_BOTTOM": [],
                    "OTHER": []
                }
                
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "")
                    if pattern_name in conflicting_groups:
                        conflicting_groups[pattern_name].append(pattern)
                    else:
                        conflicting_groups["OTHER"].append(pattern)
                
                # Resolve conflicts within each group
                resolved_list = []
                
                # Handle HEAD_SHOULDERS vs INVERSE_HEAD_SHOULDERS conflict
                hs_patterns = conflicting_groups["HEAD_SHOULDERS"]
                ihs_patterns = conflicting_groups["INVERSE_HEAD_SHOULDERS"]
                
                if hs_patterns and ihs_patterns:
                    # Both patterns detected - choose the one with higher confidence and more recent
                    best_hs = max(hs_patterns, key=lambda p: (p.get("confidence", 0), p.get("end_candle_index", 0)))
                    best_ihs = max(ihs_patterns, key=lambda p: (p.get("confidence", 0), p.get("end_candle_index", 0)))
                    
                    # Choose the pattern with higher confidence, or if equal, the more recent one
                    if best_hs.get("confidence", 0) > best_ihs.get("confidence", 0):
                        resolved_list.append(best_hs)
                        logger.info(f"📊 Pattern conflict resolved: Selected HEAD_SHOULDERS ({best_hs.get('confidence', 0):.1%}) over INVERSE_HEAD_SHOULDERS ({best_ihs.get('confidence', 0):.1%})")
                    elif best_ihs.get("confidence", 0) > best_hs.get("confidence", 0):
                        resolved_list.append(best_ihs)
                        logger.info(f"📊 Pattern conflict resolved: Selected INVERSE_HEAD_SHOULDERS ({best_ihs.get('confidence', 0):.1%}) over HEAD_SHOULDERS ({best_hs.get('confidence', 0):.1%})")
                    else:
                        # Equal confidence - choose the more recent one
                        if best_hs.get("end_candle_index", 0) > best_ihs.get("end_candle_index", 0):
                            resolved_list.append(best_hs)
                            logger.info(f"📊 Pattern conflict resolved: Selected HEAD_SHOULDERS (more recent) over INVERSE_HEAD_SHOULDERS")
                        else:
                            resolved_list.append(best_ihs)
                            logger.info(f"📊 Pattern conflict resolved: Selected INVERSE_HEAD_SHOULDERS (more recent) over HEAD_SHOULDERS")
                else:
                    # No conflict - add all patterns from both groups, but deduplicate HEAD_SHOULDERS
                    if hs_patterns:
                        # If multiple HEAD_SHOULDERS patterns detected, take only the best one
                        if len(hs_patterns) > 1:
                            best_hs = max(hs_patterns, key=lambda p: p.get("confidence", 0))
                            resolved_list.append(best_hs)
                            logger.debug(f"📊 Multiple HEAD_SHOULDERS patterns detected, selected best (confidence: {best_hs.get('confidence', 0):.1%})")
                        else:
                            resolved_list.extend(hs_patterns)
                    if ihs_patterns:
                        # If multiple INVERSE_HEAD_SHOULDERS patterns detected, take only the best one
                        if len(ihs_patterns) > 1:
                            best_ihs = max(ihs_patterns, key=lambda p: p.get("confidence", 0))
                            resolved_list.append(best_ihs)
                            logger.debug(f"📊 Multiple INVERSE_HEAD_SHOULDERS patterns detected, selected best (confidence: {best_ihs.get('confidence', 0):.1%})")
                        else:
                            resolved_list.extend(ihs_patterns)
                
                # Handle DOUBLE_TOP vs DOUBLE_BOTTOM conflict
                dt_patterns = conflicting_groups["DOUBLE_TOP"]
                db_patterns = conflicting_groups["DOUBLE_BOTTOM"]
                
                if dt_patterns and db_patterns:
                    # Both patterns detected - choose the one with higher confidence
                    best_dt = max(dt_patterns, key=lambda p: p.get("confidence", 0))
                    best_db = max(db_patterns, key=lambda p: p.get("confidence", 0))
                    
                    if best_dt.get("confidence", 0) > best_db.get("confidence", 0):
                        resolved_list.append(best_dt)
                        logger.info(f"📊 Pattern conflict resolved: Selected DOUBLE_TOP ({best_dt.get('confidence', 0):.1%}) over DOUBLE_BOTTOM ({best_db.get('confidence', 0):.1%})")
                    else:
                        resolved_list.append(best_db)
                        logger.info(f"📊 Pattern conflict resolved: Selected DOUBLE_BOTTOM ({best_db.get('confidence', 0):.1%}) over DOUBLE_TOP ({best_dt.get('confidence', 0):.1%})")
                else:
                    # No conflict - add all patterns from both groups
                    resolved_list.extend(dt_patterns)
                    resolved_list.extend(db_patterns)
                
                # Handle HEAD_SHOULDERS vs DOUBLE_BOTTOM conflict (NEW!)
                hs_patterns = conflicting_groups["HEAD_SHOULDERS"]
                if hs_patterns and db_patterns:
                    # Both bearish and bullish patterns detected - choose the one with higher confidence
                    best_hs = max(hs_patterns, key=lambda p: p.get("confidence", 0))
                    best_db = max(db_patterns, key=lambda p: p.get("confidence", 0))
                    
                    # Remove any existing HEAD_SHOULDERS or DOUBLE_BOTTOM patterns to avoid duplicates
                    resolved_list = [p for p in resolved_list if p not in hs_patterns and p not in db_patterns]
                    
                    # Add only the best pattern
                    if best_hs.get("confidence", 0) > best_db.get("confidence", 0):
                        resolved_list.append(best_hs)
                        logger.info(f"📊 Pattern conflict resolved: Selected HEAD_SHOULDERS ({best_hs.get('confidence', 0):.1%}) over DOUBLE_BOTTOM ({best_db.get('confidence', 0):.1%})")
                    else:
                        resolved_list.append(best_db)
                        logger.info(f"📊 Pattern conflict resolved: Selected DOUBLE_BOTTOM ({best_db.get('confidence', 0):.1%}) over HEAD_SHOULDERS ({best_hs.get('confidence', 0):.1%})")
                elif hs_patterns:
                    # Only HEAD_SHOULDERS patterns - check if already added to avoid duplicates
                    if not any(p.get("pattern") == "HEAD_SHOULDERS" for p in resolved_list):
                        resolved_list.extend(hs_patterns)
                elif db_patterns:
                    # Only DOUBLE_BOTTOM patterns - check if already added to avoid duplicates
                    if not any(p.get("pattern") == "DOUBLE_BOTTOM" for p in resolved_list):
                        pass  # Already added above
                
                # Add all other non-conflicting patterns
                resolved_list.extend(conflicting_groups["OTHER"])
                
                resolved_patterns[pattern_type] = resolved_list
            
            return resolved_patterns
            
        except Exception as e:
            logger.error(f"❌ Pattern conflict resolution failed: {e}")
            return patterns  # Return original patterns if resolution fails
    
    def _determine_market_setup(self, patterns: Dict[str, List[Dict[str, Any]]], 
                               overall_confidence: float) -> Dict[str, Any]:
        """Determine overall market setup based on patterns (already conflict-resolved)"""
        try:
            # Patterns are already conflict-resolved in analyze_patterns()
            # No need to resolve again - just count by direction
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0
            
            for pattern_list in patterns.values():
                for pattern in pattern_list:
                    direction = pattern.get("direction", "NEUTRAL")
                    if direction == "BULLISH":
                        bullish_count += 1
                    elif direction == "BEARISH":
                        bearish_count += 1
                    else:
                        neutral_count += 1
            
            # Determine setup
            if bullish_count > bearish_count and bullish_count > neutral_count:
                setup = "BULLISH_SETUP"
                strength = "STRONG" if bullish_count >= 3 else "MODERATE"
            elif bearish_count > bullish_count and bearish_count > neutral_count:
                setup = "BEARISH_SETUP"
                strength = "STRONG" if bearish_count >= 3 else "MODERATE"
            elif neutral_count > 0:
                setup = "NEUTRAL_SETUP"
                strength = "MODERATE"
            else:
                setup = "MIXED_SETUP"
                strength = "WEAK"
            
            return {
                "setup": setup,
                "strength": strength,
                "bullish_patterns": bullish_count,
                "bearish_patterns": bearish_count,
                "neutral_patterns": neutral_count,
                "overall_confidence": overall_confidence,
                "recommendation": self._get_trading_recommendation(setup, strength, overall_confidence)
            }
            
        except Exception as e:
            logger.error(f"❌ Market setup determination failed: {e}")
            return {"setup": "UNKNOWN", "strength": "WEAK", "recommendation": "NEUTRAL"}
    
    def _get_trading_recommendation(self, setup: str, strength: str, confidence: float) -> str:
        """Get trading recommendation based on setup"""
        if confidence < 0.4:
            return "NEUTRAL"
        
        if setup == "BULLISH_SETUP":
            if strength == "STRONG" and confidence > 0.7:
                return "STRONG_BUY"
            elif strength == "MODERATE" and confidence > 0.6:
                return "BUY"
            else:
                return "WEAK_BUY"
        elif setup == "BEARISH_SETUP":
            if strength == "STRONG" and confidence > 0.7:
                return "STRONG_SELL"
            elif strength == "MODERATE" and confidence > 0.6:
                return "SELL"
            else:
                return "WEAK_SELL"
        else:
            return "NEUTRAL"
    
