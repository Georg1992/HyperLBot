#!/usr/bin/env python3
"""
Pattern Recognition Engine Module
Main orchestrator for pattern detection using specialized detectors
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger

from .patterns import (
    CandlestickPatternDetector,
    ReversalPatternDetector,
    TrianglePatternDetector,
    ChannelPatternDetector,
    WedgePatternDetector,
    ContinuationPatternDetector,
    TrendPatternDetector
)

class PatternRecognitionEngine:
    """Recognizes trading patterns for BTC market setups using specialized detectors"""
    
    def __init__(self, symbol: str = "BTC"):
        # Trading symbol
        self.symbol = symbol
        
        # Initialize pattern detectors
        self.detectors = {
            "candlestick": CandlestickPatternDetector(),
            "reversal": ReversalPatternDetector(),
            "triangle": TrianglePatternDetector(),
            "channel": ChannelPatternDetector(),
            "wedge": WedgePatternDetector(),
            "continuation": ContinuationPatternDetector(),
            "trend": TrendPatternDetector()
        }
        
        # Combine all pattern expiration times
        self.pattern_expiration = {}
        for detector in self.detectors.values():
            self.pattern_expiration.update(detector.pattern_expiration)
        
        # Pattern history to track first detection time
        self.pattern_history = {}
        
        # Caching to prevent excessive recalculation
        self._last_candle_hash = None
        self._last_analysis_time = 0
        
        logger.info("📊 Pattern Recognition Engine initialized")
        logger.info(f"   ⚡ {len(self.pattern_expiration)} pattern types with expiration times")
    
    def analyze_patterns(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze candles for trading patterns with caching to prevent excessive recalculation
        
        Args:
            candles: List of candle data dictionaries
            
        Returns:
            Dictionary containing patterns, confidence, and status
        """
        try:
            if not candles:
                return {"patterns": [], "overall_confidence": 0.0, "status": "no_data"}
            
            current_time = time.time()
            
            # Check if we need to recalculate
            candle_hash = self._calculate_candle_data_hash(candles)
            if (self._last_candle_hash == candle_hash and 
                current_time - self._last_analysis_time < 60):  # Cache for 1 minute
                return self._get_cached_result()
            
            logger.debug(f"📊 Performing fresh pattern analysis on {len(candles)} candles")
            
            # Extract price data
            prices = self._extract_price_data(candles)
            
            # Detect patterns using specialized detectors
            patterns = {
                "reversal_patterns": self.detectors["reversal"].detect_patterns(prices),
                "continuation_patterns": self.detectors["continuation"].detect_patterns(prices),
                "triangle_patterns": self.detectors["triangle"].detect_patterns(prices),
                "channel_patterns": self.detectors["channel"].detect_patterns(prices),
                "wedge_patterns": self.detectors["wedge"].detect_patterns(prices),
                "trend_patterns": self.detectors["trend"].detect_patterns(prices),
                "candlestick_patterns": self.detectors["candlestick"].detect_patterns(candles)
            }
            
            # Calculate pattern birth times
            patterns = self._calculate_pattern_birth_times(patterns, candles, current_time)
            
            # Track pattern timestamps
            self._track_pattern_timestamps(patterns, current_time)
            
            # Filter expired patterns
            patterns = self._filter_expired_patterns(patterns, current_time)
            
            # Clean up expired patterns from history
            self._cleanup_expired_pattern_history(current_time)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(patterns)
            
            # Prepare result
            result = {
                "patterns": self._flatten_patterns(patterns),
                "overall_confidence": overall_confidence,
                "status": "ok",
                "timestamp": current_time
            }
            
            # Cache the result
            self._last_candle_hash = candle_hash
            self._last_analysis_time = current_time
            self._cached_result = result
            
            logger.info(f"📊 Pattern analysis complete: {len(result['patterns'])} patterns, {overall_confidence:.1%} confidence")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}")
            return {"patterns": [], "overall_confidence": 0.0, "status": "error", "error": str(e)}
    
    def _calculate_candle_data_hash(self, candles: List[Dict[str, Any]]) -> str:
        """Calculate hash of candle data for caching"""
        if not candles:
            return ""
        
        # Use last 10 candles for hash calculation
        recent_candles = candles[-10:] if len(candles) >= 10 else candles
        hash_data = []
        
        for candle in recent_candles:
            hash_data.append(f"{candle.get('timestamp', 0)}_{candle.get('close', 0)}")
        
        return hash(tuple(hash_data))
    
    def _get_cached_result(self) -> Dict[str, Any]:
        """Get cached analysis result"""
        return getattr(self, '_cached_result', {"patterns": [], "overall_confidence": 0.0, "status": "cached"})
    
    def _extract_price_data(self, candles: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Extract price data from candles"""
        return {
            "high": [float(candle.get("high", 0)) for candle in candles],
            "low": [float(candle.get("low", 0)) for candle in candles],
            "close": [float(candle.get("close", 0)) for candle in candles],
            "open": [float(candle.get("open", 0)) for candle in candles]
        }
    
    def _calculate_pattern_birth_times(self, patterns: Dict[str, List[Dict[str, Any]]], candles: List[Dict[str, Any]], current_time: float) -> Dict[str, List[Dict[str, Any]]]:
        """Calculate pattern birth times using actual pattern indices"""
        try:
            if not candles:
                return patterns
            
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    try:
                        # Use actual pattern indices to get timestamp
                        start_idx = pattern.get("start_candle_index", 0)
                        if start_idx < len(candles):
                            pattern_timestamp = candles[start_idx].get("timestamp", current_time * 1000)
                            pattern_birth_time = pattern_timestamp / 1000.0  # Convert to seconds
                            age_minutes = (current_time - pattern_birth_time) / 60.0
                            pattern["age_minutes"] = age_minutes
                            
                            logger.debug(f"🕐 Pattern {pattern.get('pattern', 'unknown')}: age: {age_minutes:.1f}m")
                        else:
                            pattern["age_minutes"] = 0
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to calculate birth time for pattern: {e}")
                        pattern["age_minutes"] = 0
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Pattern birth time calculation failed: {e}")
            return patterns
    
    def _track_pattern_timestamps(self, patterns: Dict[str, List[Dict[str, Any]]], current_time: float):
        """Track when patterns were first detected"""
        try:
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "unknown")
                    pattern_key = self._get_pattern_key(pattern)
                    
                    if pattern_key not in self.pattern_history:
                        self.pattern_history[pattern_key] = current_time
                        logger.info(f"🆕 NEW PATTERN DETECTED: {pattern_name} born {pattern.get('age_minutes', 0):.1f}m ago (key: {pattern_key})")
            
        except Exception as e:
            logger.error(f"❌ Pattern timestamp tracking failed: {e}")
    
    def _filter_expired_patterns(self, patterns: Dict[str, List[Dict[str, Any]]], current_time: float) -> Dict[str, List[Dict[str, Any]]]:
        """Filter out expired patterns based on their age"""
        try:
            filtered_patterns = {}
            
            for category, pattern_list in patterns.items():
                filtered_list = []
                
                for pattern in pattern_list:
                    pattern_name = pattern.get("pattern", "unknown")
                    age_minutes = pattern.get("age_minutes", 0)
                    max_age = self.pattern_expiration.get(pattern_name, 40)
                    
                    if age_minutes <= max_age:
                        filtered_list.append(pattern)
                        logger.debug(f"⏰ Pattern VALID: {pattern_name} (age: {age_minutes:.1f}m / max: {max_age}m, confidence: {pattern.get('confidence', 0):.1%})")
                    else:
                        logger.debug(f"⏰ Pattern EXPIRED: {pattern_name} (age: {age_minutes:.1f}m / max: {max_age}m)")
                
                filtered_patterns[category] = filtered_list
            
            return filtered_patterns
            
        except Exception as e:
            logger.error(f"❌ Pattern expiration filtering failed: {e}")
            return patterns
    
    def _cleanup_expired_pattern_history(self, current_time: float):
        """Clean up expired patterns from history"""
        try:
            expired_keys = []
            
            for pattern_key, first_detected_time in self.pattern_history.items():
                age_minutes = (current_time - first_detected_time) / 60.0
                pattern_name = pattern_key.split("_")[0] if "_" in pattern_key else "unknown"
                max_age = self.pattern_expiration.get(pattern_name, 40)
                
                if age_minutes > max_age * 2:  # Keep history for 2x expiration time
                    expired_keys.append(pattern_key)
            
            for key in expired_keys:
                del self.pattern_history[key]
                
        except Exception as e:
            logger.error(f"❌ Pattern history cleanup failed: {e}")
    
    def _get_pattern_key(self, pattern: Dict[str, Any]) -> str:
        """Generate unique key for pattern tracking"""
        try:
            pattern_name = pattern.get("pattern", "unknown")
            pattern_high = pattern.get("pattern_high", 0)
            pattern_low = pattern.get("pattern_low", 0)
            return f"{pattern_name}_{pattern_high}_{pattern_low}"
        except Exception:
            return "unknown_0_0"
    
    def _calculate_overall_confidence(self, patterns: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate overall confidence from all detected patterns"""
        try:
            all_patterns = []
            for pattern_list in patterns.values():
                all_patterns.extend(pattern_list)
            
            if not all_patterns:
                return 0.0
            
            total_confidence = sum(pattern.get("confidence", 0) for pattern in all_patterns)
            return total_confidence / len(all_patterns)
            
        except Exception as e:
            logger.error(f"❌ Overall confidence calculation failed: {e}")
            return 0.0
    
    def _flatten_patterns(self, patterns: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Flatten patterns into a single list for dashboard compatibility"""
        flattened = []
        
        for pattern_list in patterns.values():
            flattened.extend(pattern_list)
        
        return flattened
    
    def invalidate_cache(self):
        """Invalidate pattern analysis cache"""
        self._last_candle_hash = None
        self._last_analysis_time = 0
        logger.debug("🔄 Pattern analysis cache invalidated")
