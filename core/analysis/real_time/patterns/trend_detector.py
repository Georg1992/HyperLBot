#!/usr/bin/env python3
"""
Trend Pattern Detector
Detects trend patterns like Trend Change
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from .base_detector import BasePatternDetector

class TrendPatternDetector(BasePatternDetector):
    """Detects trend patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup trend pattern expiration times"""
        self.pattern_expiration = {
            "TREND_CHANGE": 15,
        }
    
    def detect_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect trend patterns"""
        patterns = []
        
        # Trend Change
        trend_change = self._detect_trend_change(prices)
        if trend_change:
            patterns.append(trend_change)
        
        return patterns
    
    def _detect_trend_change(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect trend change pattern"""
        try:
            closes = prices["close"]
            if len(closes) < 10:
                return None
            
            # Compare recent trend with earlier trend
            recent_closes = closes[-5:]
            earlier_closes = closes[-10:-5]
            
            recent_slope = self._calculate_slope(recent_closes)
            earlier_slope = self._calculate_slope(earlier_closes)
            
            # Check for trend reversal
            if ((earlier_slope > 0.001 and recent_slope < -0.001) or  # Bullish to bearish
                (earlier_slope < -0.001 and recent_slope > 0.001)):   # Bearish to bullish
                
                quality = 0.85
                direction = "BULLISH" if recent_slope > 0 else "BEARISH"
                
                return self._create_pattern(
                    "TREND_CHANGE", "REVERSAL", direction, quality,
                    len(closes) - 10, len(closes) - 1, max(closes[-10:]), min(closes[-10:])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Trend change detection failed: {e}")
            return None
