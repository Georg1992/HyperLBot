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
            
            # Calculate average price for percentage calculation
            avg_price = (sum(recent_highs) + sum(recent_lows)) / (len(recent_highs) + len(recent_lows))
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Convert slopes to percentage per candle
            high_slope_pct = abs(high_slope / avg_price) if avg_price > 0 else 0
            low_slope_pct = abs(low_slope / avg_price) if avg_price > 0 else 0
            
            # Check if both slopes are horizontal (< 0.05% per candle = ~0.5% over 10 candles)
            if high_slope_pct < 0.0005 and low_slope_pct < 0.0005:
                quality = 0.75
                return self._create_pattern(
                    "HORIZONTAL_CHANNEL", "CONTINUATION", "NEUTRAL", quality,
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
            
            # Calculate average price for percentage calculation
            avg_price = (sum(recent_highs) + sum(recent_lows)) / (len(recent_highs) + len(recent_lows))
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Convert slopes to percentage per candle
            high_slope_pct = (high_slope / avg_price) if avg_price > 0 else 0
            low_slope_pct = (low_slope / avg_price) if avg_price > 0 else 0
            
            # Check if both slopes are positive and parallel (within 0.03% per candle difference)
            if high_slope_pct > 0.0001 and low_slope_pct > 0.0001 and abs(high_slope_pct - low_slope_pct) < 0.0003:
                quality = 0.80
                return self._create_pattern(
                    "ASCENDING_CHANNEL", "CONTINUATION", "BULLISH", quality,
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
            
            # Calculate average price for percentage calculation
            avg_price = (sum(recent_highs) + sum(recent_lows)) / (len(recent_highs) + len(recent_lows))
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Convert slopes to percentage per candle
            high_slope_pct = (high_slope / avg_price) if avg_price > 0 else 0
            low_slope_pct = (low_slope / avg_price) if avg_price > 0 else 0
            
            # Check if both slopes are negative and parallel (within 0.03% per candle difference)
            if high_slope_pct < -0.0001 and low_slope_pct < -0.0001 and abs(high_slope_pct - low_slope_pct) < 0.0003:
                quality = 0.80
                return self._create_pattern(
                    "DESCENDING_CHANNEL", "CONTINUATION", "BEARISH", quality,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Descending channel detection failed: {e}")
            return None
