#!/usr/bin/env python3
"""
Channel Pattern Detector
Detects channel patterns like Horizontal, Ascending, and Descending channels
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from .base_detector import BasePatternDetector

class ChannelPatternDetector(BasePatternDetector):
    """Detects channel patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup channel pattern expiration times"""
        self.pattern_expiration = {
            "HORIZONTAL_CHANNEL": 50,
            "ASCENDING_CHANNEL": 50,
            "DESCENDING_CHANNEL": 50,
        }
    
    def detect_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect channel patterns"""
        patterns = []
        
        # Horizontal Channel
        horizontal = self._detect_horizontal_channel(prices)
        if horizontal:
            patterns.append(horizontal)
        
        # Ascending Channel
        ascending = self._detect_ascending_channel(prices)
        if ascending:
            patterns.append(ascending)
        
        # Descending Channel
        descending = self._detect_descending_channel(prices)
        if descending:
            patterns.append(descending)
        
        return patterns
    
    def _detect_horizontal_channel(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect horizontal channel pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for horizontal trend with parallel support/resistance
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Check if both slopes are horizontal (parallel channel)
            if abs(high_slope) < 0.0001 and abs(low_slope) < 0.0001:
                confidence = 0.67
                return self._create_pattern(
                    "HORIZONTAL_CHANNEL", "CONTINUATION", "NEUTRAL", confidence,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Horizontal channel detection failed: {e}")
            return None
    
    def _detect_ascending_channel(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect ascending channel pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for ascending trend with parallel support/resistance
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Check if both slopes are positive and similar (ascending channel)
            if high_slope > 0 and low_slope > 0 and abs(high_slope - low_slope) < 0.001:
                confidence = 0.90
                return self._create_pattern(
                    "ASCENDING_CHANNEL", "CONTINUATION", "BULLISH", confidence,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ascending channel detection failed: {e}")
            return None
    
    def _detect_descending_channel(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect descending channel pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for descending trend with parallel support/resistance
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Check if both slopes are negative and similar (descending channel)
            if high_slope < 0 and low_slope < 0 and abs(high_slope - low_slope) < 0.001:
                confidence = 0.90
                return self._create_pattern(
                    "DESCENDING_CHANNEL", "CONTINUATION", "BEARISH", confidence,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Descending channel detection failed: {e}")
            return None
