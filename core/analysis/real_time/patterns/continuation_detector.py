#!/usr/bin/env python3
"""
Continuation Pattern Detector
Detects continuation patterns like Bullish and Bearish continuation
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from .base_detector import BasePatternDetector

class ContinuationPatternDetector(BasePatternDetector):
    """Detects continuation patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup continuation pattern expiration times"""
        self.pattern_expiration = {
            "BULLISH_CONTINUATION": 15,
            "BEARISH_CONTINUATION": 15,
        }
    
    def detect_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
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
    
    def _detect_bullish_continuation(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect bullish continuation pattern"""
        try:
            closes = prices["close"]
            if len(closes) < 5:
                return None
            
            # Look for upward trend
            recent_closes = closes[-5:]
            slope = self._calculate_slope(recent_closes)
            
            if slope > 0.001:  # Positive slope
                quality = 0.90
                return self._create_pattern(
                    "BULLISH_CONTINUATION", "CONTINUATION", "BULLISH", quality,
                    len(closes) - 5, len(closes) - 1, max(recent_closes), min(recent_closes)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Bullish continuation detection failed: {e}")
            return None
    
    def _detect_bearish_continuation(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect bearish continuation pattern"""
        try:
            closes = prices["close"]
            if len(closes) < 5:
                return None
            
            # Look for downward trend
            recent_closes = closes[-5:]
            slope = self._calculate_slope(recent_closes)
            
            if slope < -0.001:  # Negative slope
                quality = 0.90
                return self._create_pattern(
                    "BEARISH_CONTINUATION", "CONTINUATION", "BEARISH", quality,
                    len(closes) - 5, len(closes) - 1, max(recent_closes), min(recent_closes)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Bearish continuation detection failed: {e}")
            return None
