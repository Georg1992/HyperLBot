#!/usr/bin/env python3
"""
Wedge Pattern Detector
Detects wedge patterns like Rising and Falling wedges
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from .base_detector import BasePatternDetector

class WedgePatternDetector(BasePatternDetector):
    """Detects wedge patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup wedge pattern expiration times"""
        self.pattern_expiration = {
            "RISING_WEDGE": 15,
            "FALLING_WEDGE": 15,
        }
    
    def detect_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
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
    
    def _detect_rising_wedge(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect rising wedge pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for converging ascending trend
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Check if both slopes are positive but converging (low slope > high slope)
            if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
                quality = 0.80
                return self._create_pattern(
                    "RISING_WEDGE", "REVERSAL", "BEARISH", quality,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Rising wedge detection failed: {e}")
            return None
    
    def _detect_falling_wedge(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect falling wedge pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for converging descending trend
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Check if both slopes are negative but converging (high slope < low slope)
            if high_slope < 0 and low_slope < 0 and high_slope < low_slope:
                quality = 0.80
                return self._create_pattern(
                    "FALLING_WEDGE", "REVERSAL", "BULLISH", quality,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Falling wedge detection failed: {e}")
            return None
