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
        
        # No internal caching - rely on centralized cache system
        # Centralized cache handles all caching logic
        
        logger.info("📊 Pattern Recognition Engine initialized")
        logger.info(f"   ⚡ {len(self.pattern_expiration)} pattern types with expiration times")
        logger.info("   🗄️ Using centralized cache system (no internal cache)")
    
    def analyze_patterns(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze candles for trading patterns
        
        Caching is handled by CentralizedCache system - this method always performs fresh analysis.
        The cache system will determine if analysis is needed based on:
        - New 5-minute candle closes
        - Cache TTL expiration
        
        Args:
            candles: List of candle data dictionaries
            
        Returns:
            Dictionary containing patterns, confidence, and status
        """
        try:
            if not candles:
                return {"patterns": [], "overall_confidence": 0.0, "status": "no_data"}
            
            current_time = time.time()
            
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
            
            # Prepare result with BOTH flat and nested structures for compatibility
            # Flat array for chart drawing, nested for text display
            result = {
                "patterns": self._flatten_patterns(patterns),  # Flat array for chart overlays
                "patterns_nested": patterns,  # Nested structure for text display
                "overall_confidence": overall_confidence,
                "status": "ok",
                "timestamp": current_time,
                "last_candle_timestamp": candles[-1].get("timestamp", current_time) if candles else current_time  # Track last candle for change detection
            }
            
            # No internal caching - CentralizedCache handles this
            logger.info(f"📊 Pattern analysis complete: {len(result['patterns'])} patterns, {overall_confidence:.1%} confidence")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}")
            return {"patterns": [], "overall_confidence": 0.0, "status": "error", "error": str(e)}
    
    def _calculate_candle_data_hash(self, candles: List[Dict[str, Any]]) -> str:
        """
        Calculate hash of candle data for change detection
        
        Note: This is used for detecting candle changes, not for caching.
        Caching is handled by CentralizedCache system.
        """
        if not candles:
            return ""
        
        # Use last candle timestamp and close price to detect new candles
        last_candle = candles[-1] if candles else None
        if last_candle:
            return f"{last_candle.get('timestamp', 0)}_{last_candle.get('close', 0)}"
        return ""
    
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
                            pattern_timestamp = candles[start_idx].get("timestamp", current_time)
                            
                            # Handle both seconds and milliseconds timestamps
                            # If timestamp is > 1e10, it's in milliseconds, convert to seconds
                            if pattern_timestamp > 1e10:
                                pattern_birth_time = pattern_timestamp / 1000.0
                            else:
                                pattern_birth_time = pattern_timestamp
                            
                            age_minutes = (current_time - pattern_birth_time) / 60.0
                            
                            # Sanity check: age should be reasonable (0 to 1000 minutes max)
                            if age_minutes < 0 or age_minutes > 1000:
                                logger.warning(f"⚠️ Invalid pattern age: {age_minutes:.1f}m for pattern {pattern.get('pattern', 'unknown')}, using 0")
                                pattern["age_minutes"] = 0
                            else:
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
        """
        Invalidate pattern analysis cache
        
        Note: This method is kept for compatibility, but caching is now handled
        by CentralizedCache system. Call CentralizedCache.invalidate() instead.
        """
        logger.debug("🔄 Pattern analysis cache invalidation requested (handled by CentralizedCache)")
