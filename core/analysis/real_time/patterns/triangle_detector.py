#!/usr/bin/env python3
"""
Triangle Pattern Detector
Detects triangle patterns like Ascending, Descending, and Symmetrical triangles
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from .base_detector import BasePatternDetector

class TrianglePatternDetector(BasePatternDetector):
    """Detects triangle patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup triangle pattern expiration times"""
        self.pattern_expiration = {
            "ASCENDING_TRIANGLE": 15,
            "DESCENDING_TRIANGLE": 15,
            "SYMMETRICAL_TRIANGLE": 20,
        }
    
    def detect_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Detect triangle patterns"""
        patterns = []
        
        # Ascending Triangle
        asc_triangle = self._detect_ascending_triangle(prices)
        if asc_triangle:
            patterns.append(asc_triangle)
        
        # Descending Triangle
        desc_triangle = self._detect_descending_triangle(prices)
        if desc_triangle:
            patterns.append(desc_triangle)
        
        # Symmetrical Triangle
        sym_triangle = self._detect_symmetrical_triangle(prices)
        if sym_triangle:
            patterns.append(sym_triangle)
        
        return patterns
    
    def _detect_ascending_triangle(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect ascending triangle pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for horizontal resistance and ascending support
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate average price for percentage calculation
            avg_price = (sum(recent_highs) + sum(recent_lows)) / (len(recent_highs) + len(recent_lows))
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Convert slopes to percentage per candle
            high_slope_pct = abs(high_slope / avg_price) if avg_price > 0 else 0
            low_slope_pct = (low_slope / avg_price) if avg_price > 0 else 0
            
            # Check if resistance is horizontal (<0.05% per candle) and support is ascending (>0.01% per candle)
            if high_slope_pct < 0.0005 and low_slope_pct > 0.0001:
                confidence = 0.80
                return self._create_pattern(
                    "ASCENDING_TRIANGLE", "CONTINUATION", "BULLISH", confidence,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ascending triangle detection failed: {e}")
            return None
    
    def _detect_descending_triangle(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect descending triangle pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for descending resistance and horizontal support
            recent_highs = highs[-10:]
            recent_lows = lows[-10:]
            
            # Calculate average price for percentage calculation
            avg_price = (sum(recent_highs) + sum(recent_lows)) / (len(recent_highs) + len(recent_lows))
            
            # Calculate slopes
            high_slope = self._calculate_slope(recent_highs)
            low_slope = self._calculate_slope(recent_lows)
            
            # Convert slopes to percentage per candle
            high_slope_pct = (high_slope / avg_price) if avg_price > 0 else 0
            low_slope_pct = abs(low_slope / avg_price) if avg_price > 0 else 0
            
            # Check if resistance is descending (<-0.01% per candle) and support is horizontal (<0.05% per candle)
            if high_slope_pct < -0.0001 and low_slope_pct < 0.0005:
                confidence = 0.80
                return self._create_pattern(
                    "DESCENDING_TRIANGLE", "CONTINUATION", "BEARISH", confidence,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Descending triangle detection failed: {e}")
            return None
    
    def _detect_symmetrical_triangle(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect symmetrical triangle pattern"""
        try:
            highs = prices["high"]
            lows = prices["low"]
            
            if len(highs) < 10:
                return None
            
            # Look for converging resistance and support
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
            
            # Check if resistance is descending and support is ascending (converging)
            # Slopes should be roughly equal in magnitude but opposite direction
            if high_slope_pct < -0.0001 and low_slope_pct > 0.0001:
                confidence = 0.75
                return self._create_pattern(
                    "SYMMETRICAL_TRIANGLE", "CONTINUATION", "NEUTRAL", confidence,
                    len(highs) - 10, len(highs) - 1, max(recent_highs), min(recent_lows)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Symmetrical triangle detection failed: {e}")
            return None
