#!/usr/bin/env python3
"""
Reversal Pattern Detector
Detects reversal patterns like Head & Shoulders, Double Top/Bottom, Triple Top/Bottom, etc.
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from .base_detector import BasePatternDetector

class ReversalPatternDetector(BasePatternDetector):
    """Detects reversal patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup reversal pattern expiration times"""
        self.pattern_expiration = {
            "HEAD_SHOULDERS": 30,
            "INVERSE_HEAD_SHOULDERS": 30,
            "DOUBLE_TOP": 25,
            "DOUBLE_BOTTOM": 25,
            "TRIPLE_TOP": 35,
            "TRIPLE_BOTTOM": 35,
            "TREND_CHANGE": 15,
        }
    
    def detect_patterns(self, prices: Dict[str, List[float]]) -> List[Dict[str, Any]]:
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
        
        # Triple Top
        triple_top = self._detect_triple_top(prices)
        if triple_top:
            patterns.append(triple_top)
        
        # Triple Bottom
        triple_bottom = self._detect_triple_bottom(prices)
        if triple_bottom:
            patterns.append(triple_bottom)
        
        return patterns
    
    def _detect_double_top(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect double top pattern"""
        try:
            highs = prices["high"]
            if len(highs) < 10:
                return None
            
            # Find peaks
            peaks = self._find_peaks(highs)
            if len(peaks) < 2:
                return None
            
            # Look for two similar peaks
            recent_peaks = peaks[-2:]
            peak1_idx, peak1_val = recent_peaks[0]
            peak2_idx, peak2_val = recent_peaks[1]
            
            # Check if peaks are similar in height (within 2%)
            if abs(peak1_val - peak2_val) / max(peak1_val, peak2_val) < 0.02:
                # Find valley between peaks
                valley_idx = self._find_valley_between(highs, peak1_idx, peak2_idx)
                if valley_idx:
                    valley_val = highs[valley_idx]
                    
                    # Check if valley is significantly lower than peaks
                    if valley_val < min(peak1_val, peak2_val) * 0.95:
                        confidence = 0.80
                        return self._create_pattern(
                            "DOUBLE_TOP", "REVERSAL", "BEARISH", confidence,
                            peak1_idx, peak2_idx, max(peak1_val, peak2_val), valley_val
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Double top detection failed: {e}")
            return None
    
    def _detect_double_bottom(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect double bottom pattern"""
        try:
            lows = prices["low"]
            if len(lows) < 10:
                return None
            
            # Find valleys
            valleys = self._find_valleys(lows)
            if len(valleys) < 2:
                return None
            
            # Look for two similar valleys
            recent_valleys = valleys[-2:]
            valley1_idx, valley1_val = recent_valleys[0]
            valley2_idx, valley2_val = recent_valleys[1]
            
            # Check if valleys are similar in depth (within 2%)
            if abs(valley1_val - valley2_val) / max(valley1_val, valley2_val) < 0.02:
                # Find peak between valleys
                peak_idx = self._find_peak_between(lows, valley1_idx, valley2_idx)
                if peak_idx:
                    peak_val = lows[peak_idx]
                    
                    # Check if peak is significantly higher than valleys
                    if peak_val > max(valley1_val, valley2_val) * 1.05:
                        confidence = 0.80
                        return self._create_pattern(
                            "DOUBLE_BOTTOM", "REVERSAL", "BULLISH", confidence,
                            valley1_idx, valley2_idx, peak_val, min(valley1_val, valley2_val)
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Double bottom detection failed: {e}")
            return None
    
    def _detect_head_shoulders(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect head and shoulders pattern"""
        try:
            highs = prices["high"]
            if len(highs) < 15:
                return None
            
            # Find peaks
            peaks = self._find_peaks(highs)
            if len(peaks) < 3:
                return None
            
            # Look for three peaks: left shoulder, head, right shoulder
            recent_peaks = peaks[-3:]
            left_shoulder_idx, left_shoulder_val = recent_peaks[0]
            head_idx, head_val = recent_peaks[1]
            right_shoulder_idx, right_shoulder_val = recent_peaks[2]
            
            # Check if head is higher than shoulders
            if (head_val > left_shoulder_val and 
                head_val > right_shoulder_val and
                abs(left_shoulder_val - right_shoulder_val) / max(left_shoulder_val, right_shoulder_val) < 0.05):
                
                confidence = 0.85
                return self._create_pattern(
                    "HEAD_SHOULDERS", "REVERSAL", "BEARISH", confidence,
                    left_shoulder_idx, right_shoulder_idx, head_val,
                    min(highs[left_shoulder_idx:right_shoulder_idx+1])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Head and shoulders detection failed: {e}")
            return None
    
    def _detect_inverse_head_shoulders(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect inverse head and shoulders pattern"""
        try:
            lows = prices["low"]
            if len(lows) < 15:
                return None
            
            # Find valleys
            valleys = self._find_valleys(lows)
            if len(valleys) < 3:
                return None
            
            # Look for three valleys: left shoulder, head, right shoulder
            recent_valleys = valleys[-3:]
            left_shoulder_idx, left_shoulder_val = recent_valleys[0]
            head_idx, head_val = recent_valleys[1]
            right_shoulder_idx, right_shoulder_val = recent_valleys[2]
            
            # Check if head is lower than shoulders
            if (head_val < left_shoulder_val and 
                head_val < right_shoulder_val and
                abs(left_shoulder_val - right_shoulder_val) / max(left_shoulder_val, right_shoulder_val) < 0.05):
                
                confidence = 0.85
                return self._create_pattern(
                    "INVERSE_HEAD_SHOULDERS", "REVERSAL", "BULLISH", confidence,
                    left_shoulder_idx, right_shoulder_idx, max(lows[left_shoulder_idx:right_shoulder_idx+1]), head_val
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Inverse head and shoulders detection failed: {e}")
            return None
    
    def _detect_triple_top(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect triple top pattern"""
        try:
            highs = prices["high"]
            if len(highs) < 15:
                return None
            
            # Find peaks
            peaks = self._find_peaks(highs)
            if len(peaks) < 3:
                return None
            
            # Look for three similar peaks
            recent_peaks = peaks[-3:]
            peak1_idx, peak1_val = recent_peaks[0]
            peak2_idx, peak2_val = recent_peaks[1]
            peak3_idx, peak3_val = recent_peaks[2]
            
            # Check if all three peaks are similar in height (within 3%)
            if (abs(peak1_val - peak2_val) / max(peak1_val, peak2_val) < 0.03 and
                abs(peak2_val - peak3_val) / max(peak2_val, peak3_val) < 0.03 and
                abs(peak1_val - peak3_val) / max(peak1_val, peak3_val) < 0.03):
                
                # Find valleys between peaks
                valley1_idx = self._find_valley_between(highs, peak1_idx, peak2_idx)
                valley2_idx = self._find_valley_between(highs, peak2_idx, peak3_idx)
                
                if valley1_idx and valley2_idx:
                    valley1_val = highs[valley1_idx]
                    valley2_val = highs[valley2_idx]
                    
                    # Check if valleys are significantly lower than peaks
                    if (valley1_val < min(peak1_val, peak2_val) * 0.95 and
                        valley2_val < min(peak2_val, peak3_val) * 0.95):
                        
                        confidence = 0.85
                        return self._create_pattern(
                            "TRIPLE_TOP", "REVERSAL", "BEARISH", confidence,
                            peak1_idx, peak3_idx, max(peak1_val, peak2_val, peak3_val), min(valley1_val, valley2_val)
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Triple top detection failed: {e}")
            return None
    
    def _detect_triple_bottom(self, prices: Dict[str, List[float]]) -> Optional[Dict[str, Any]]:
        """Detect triple bottom pattern"""
        try:
            lows = prices["low"]
            if len(lows) < 15:
                return None
            
            # Find valleys
            valleys = self._find_valleys(lows)
            if len(valleys) < 3:
                return None
            
            # Look for three similar valleys
            recent_valleys = valleys[-3:]
            valley1_idx, valley1_val = recent_valleys[0]
            valley2_idx, valley2_val = recent_valleys[1]
            valley3_idx, valley3_val = recent_valleys[2]
            
            # Check if all three valleys are similar in depth (within 3%)
            if (abs(valley1_val - valley2_val) / max(valley1_val, valley2_val) < 0.03 and
                abs(valley2_val - valley3_val) / max(valley2_val, valley3_val) < 0.03 and
                abs(valley1_val - valley3_val) / max(valley1_val, valley3_val) < 0.03):
                
                # Find peaks between valleys
                peak1_idx = self._find_peak_between(lows, valley1_idx, valley2_idx)
                peak2_idx = self._find_peak_between(lows, valley2_idx, valley3_idx)
                
                if peak1_idx and peak2_idx:
                    peak1_val = lows[peak1_idx]
                    peak2_val = lows[peak2_idx]
                    
                    # Check if peaks are significantly higher than valleys
                    if (peak1_val > max(valley1_val, valley2_val) * 1.05 and
                        peak2_val > max(valley2_val, valley3_val) * 1.05):
                        
                        confidence = 0.85
                        return self._create_pattern(
                            "TRIPLE_BOTTOM", "REVERSAL", "BULLISH", confidence,
                            valley1_idx, valley3_idx, max(peak1_val, peak2_val), min(valley1_val, valley2_val, valley3_val)
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Triple bottom detection failed: {e}")
            return None
