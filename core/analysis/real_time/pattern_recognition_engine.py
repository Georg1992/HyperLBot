#!/usr/bin/env python3
"""
Pattern Recognition Engine Module
Identifies important trading patterns for BTC market setups
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

class PatternRecognitionEngine:
    """Recognizes trading patterns for BTC market setups"""
    
    def __init__(self):
        # Pattern detection parameters
        self.min_pattern_length = 5  # Minimum candles for pattern
        self.max_pattern_length = 50  # Maximum candles for pattern
        self.tolerance = 0.02  # 2% tolerance for pattern matching
        
        # Pattern confidence thresholds
        self.high_confidence = 0.8
        self.medium_confidence = 0.6
        self.low_confidence = 0.4
        
        logger.info("📊 Pattern Recognition Engine initialized")
    
    def analyze_patterns(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze candles for trading patterns
        
        Args:
            candles: List of candle data with OHLC
            
        Returns:
            Dictionary with pattern analysis
        """
        try:
            if len(candles) < self.min_pattern_length:
                return self._get_default_pattern_analysis()
            
            # Extract price data
            prices = self._extract_price_data(candles)
            
            # Detect all patterns
            patterns = {
                "reversal_patterns": self._detect_reversal_patterns(prices),
                "continuation_patterns": self._detect_continuation_patterns(prices),
                "triangle_patterns": self._detect_triangle_patterns(prices),
                "channel_patterns": self._detect_channel_patterns(prices),
                "wedge_patterns": self._detect_wedge_patterns(prices),
                "trend_patterns": self._detect_trend_patterns(prices)
            }
            
            # Calculate overall pattern confidence
            overall_confidence = self._calculate_overall_confidence(patterns)
            
            # Determine market setup
            market_setup = self._determine_market_setup(patterns, overall_confidence)
            
            return {
                "patterns": patterns,
                "overall_confidence": overall_confidence,
                "market_setup": market_setup,
                "pattern_count": sum(len(p) for p in patterns.values()),
                "timestamp": time.time(),
                "data_source": "pattern_recognition"
            }
            
        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}")
            return self._get_default_pattern_analysis()
    
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
                return {
                    "pattern": "SYMMETRICAL_TRIANGLE",
                    "type": "CONTINUATION",
                    "direction": "NEUTRAL",
                    "confidence": confidence,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "convergence_rate": convergence_rate,
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
                return {
                    "pattern": "RISING_WEDGE",
                    "type": "REVERSAL",
                    "direction": "BEARISH",
                    "confidence": confidence,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "convergence_rate": convergence_rate,
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
                return {
                    "pattern": "FALLING_WEDGE",
                    "type": "REVERSAL",
                    "direction": "BULLISH",
                    "confidence": confidence,
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
    
    def _determine_market_setup(self, patterns: Dict[str, List[Dict[str, Any]]], 
                               overall_confidence: float) -> Dict[str, Any]:
        """Determine overall market setup based on patterns"""
        try:
            # Count patterns by direction
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
            return {"setup": "UNKNOWN", "strength": "WEAK", "recommendation": "HOLD"}
    
    def _get_trading_recommendation(self, setup: str, strength: str, confidence: float) -> str:
        """Get trading recommendation based on setup"""
        if confidence < 0.4:
            return "HOLD"
        
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
            return "HOLD"
    
    def _get_default_pattern_analysis(self) -> Dict[str, Any]:
        """Return default analysis when pattern detection fails"""
        return {
            "patterns": {
                "reversal_patterns": [],
                "continuation_patterns": [],
                "triangle_patterns": [],
                "channel_patterns": [],
                "wedge_patterns": [],
                "trend_patterns": []
            },
            "overall_confidence": 0.0,
            "market_setup": {
                "setup": "UNKNOWN",
                "strength": "WEAK",
                "bullish_patterns": 0,
                "bearish_patterns": 0,
                "neutral_patterns": 0,
                "overall_confidence": 0.0,
                "recommendation": "HOLD"
            },
            "pattern_count": 0,
            "timestamp": time.time(),
            "data_source": "default_fallback"
        }
