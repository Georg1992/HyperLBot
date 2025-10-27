#!/usr/bin/env python3
"""
Candlestick Pattern Detector
Detects candlestick patterns like Three White Soldiers, Engulfing, Harami, etc.
"""

from typing import Dict, List, Any, Optional
from .base_detector import BasePatternDetector

class CandlestickPatternDetector(BasePatternDetector):
    """Detects candlestick patterns"""
    
    def _setup_pattern_expiration(self):
        """Setup candlestick pattern expiration times"""
        self.pattern_expiration = {
            "THREE_WHITE_SOLDIERS": 20,
            "THREE_BLACK_CROWS": 20,
            "BULLISH_ENGULFING": 10,
            "BEARISH_ENGULFING": 10,
            "HAMMER": 10,
            "DOJI": 10,
            "SHOOTING_STAR": 10,
            "BULLISH_HARAMI": 10,
            "BEARISH_HARAMI": 10,
            "MORNING_STAR": 15,
            "EVENING_STAR": 15,
        }
    
    def detect_patterns(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect candlestick patterns"""
        patterns = []
        
        if len(candles) < 3:
            return patterns
        
        # Check last 3 candles for patterns
        recent_candles = candles[-3:]
        
        # Engulfing patterns (2 candles)
        if len(recent_candles) >= 2:
            engulfing = self._detect_engulfing(recent_candles[-2:])
            if engulfing:
                patterns.append(engulfing)
        
        # Harami patterns (2 candles)
        if len(recent_candles) >= 2:
            harami = self._detect_harami(recent_candles[-2:])
            if harami:
                patterns.append(harami)
        
        # Hammer, Shooting Star, Doji (single candle)
        single_pattern = self._detect_single_candlestick(recent_candles[-1])
        if single_pattern:
            patterns.append(single_pattern)
        
        # Three Soldiers/Crows (3 candles)
        if len(recent_candles) >= 3:
            three_pattern = self._detect_three_candles(recent_candles, len(candles) - 3)
            if three_pattern:
                patterns.append(three_pattern)
        
        # Morning/Evening Star (3 candles)
        if len(recent_candles) >= 3:
            star_pattern = self._detect_morning_evening_star(recent_candles, len(candles) - 3)
            if star_pattern:
                patterns.append(star_pattern)
        
        return patterns
    
    def _detect_three_candles(self, candles: List[Dict[str, Any]], offset: int = 0) -> Optional[Dict[str, Any]]:
        """Detect Three White Soldiers or Three Black Crows"""
        if len(candles) < 3:
            return None
        
        candle1 = candles[0]
        candle2 = candles[1]
        candle3 = candles[2]
        
        open1 = float(candle1.get("open", 0))
        close1 = float(candle1.get("close", 0))
        open2 = float(candle2.get("open", 0))
        close2 = float(candle2.get("close", 0))
        open3 = float(candle3.get("open", 0))
        close3 = float(candle3.get("close", 0))
        
        if not all([open1, close1, open2, close2, open3, close3]):
            return None
        
        opens = [open1, open2, open3]
        closes = [close1, close2, close3]
        
        # Three White Soldiers: three consecutive bullish candles
        if (close1 > open1 and close2 > open2 and close3 > open3 and
            close2 > close1 and close3 > close2 and
            open2 > close1 and open3 > close2):
            
            confidence = 0.85
            return self._create_pattern(
                "THREE_WHITE_SOLDIERS", "CONTINUATION", "BULLISH", confidence,
                offset, offset + 2, max(opens), min(closes), [offset, offset + 1, offset + 2]
            )
        
        # Three Black Crows: three consecutive bearish candles
        elif (close1 < open1 and close2 < open2 and close3 < open3 and
              close2 < close1 and close3 < close2 and
              open2 < close1 and open3 < close2):
            
            confidence = 0.85
            return self._create_pattern(
                "THREE_BLACK_CROWS", "CONTINUATION", "BEARISH", confidence,
                offset, offset + 2, max(opens), min(closes), [offset, offset + 1, offset + 2]
            )
        
        return None
    
    def _detect_morning_evening_star(self, candles: List[Dict[str, Any]], offset: int = 0) -> Optional[Dict[str, Any]]:
        """Detect Morning Star or Evening Star patterns"""
        if len(candles) < 3:
            return None
        
        candle1 = candles[0]
        candle2 = candles[1] 
        candle3 = candles[2]
        
        open1 = float(candle1.get("open", 0))
        close1 = float(candle1.get("close", 0))
        open2 = float(candle2.get("open", 0))
        close2 = float(candle2.get("close", 0))
        open3 = float(candle3.get("open", 0))
        close3 = float(candle3.get("close", 0))
        
        if not all([open1, close1, open2, close2, open3, close3]):
            return None
        
        # Morning Star: bearish candle, small body candle, bullish candle
        if (close1 < open1 and  # First candle bearish
            abs(close2 - open2) < (open1 - close1) * 0.3 and  # Second candle small body
            close3 > open3 and  # Third candle bullish
            close3 > (open1 + close1) / 2):  # Third candle closes above first candle midpoint
            
            confidence = 0.80
            return self._create_pattern(
                "MORNING_STAR", "REVERSAL", "BULLISH", confidence,
                offset, offset + 2, max(open1, close1, open2, close2, open3, close3),
                min(open1, close1, open2, close2, open3, close3), [offset, offset + 1, offset + 2]
            )
        
        # Evening Star: bullish candle, small body candle, bearish candle
        elif (close1 > open1 and  # First candle bullish
              abs(close2 - open2) < (close1 - open1) * 0.3 and  # Second candle small body
              close3 < open3 and  # Third candle bearish
              close3 < (open1 + close1) / 2):  # Third candle closes below first candle midpoint
            
            confidence = 0.80
            return self._create_pattern(
                "EVENING_STAR", "REVERSAL", "BEARISH", confidence,
                offset, offset + 2, max(open1, close1, open2, close2, open3, close3),
                min(open1, close1, open2, close2, open3, close3), [offset, offset + 1, offset + 2]
            )
        
        return None
    
    def _detect_engulfing(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect bullish or bearish engulfing pattern"""
        if len(candles) < 2:
            return None
        
        prev_candle = candles[0]
        curr_candle = candles[1]
        
        prev_open = float(prev_candle.get("open", 0))
        prev_close = float(prev_candle.get("close", 0))
        curr_open = float(curr_candle.get("open", 0))
        curr_close = float(curr_candle.get("close", 0))
        
        if not all([prev_open, prev_close, curr_open, curr_close]):
            return None
        
        # Bullish Engulfing: previous bearish, current bullish and engulfs previous
        if (prev_close < prev_open and  # Previous bearish
            curr_close > curr_open and  # Current bullish
            curr_open < prev_close and  # Current opens below previous close
            curr_close > prev_open):    # Current closes above previous open
            
            confidence = 0.75
            return self._create_pattern(
                "BULLISH_ENGULFING", "REVERSAL", "BULLISH", confidence,
                len(candles) - 2, len(candles) - 1, max(prev_open, curr_close), min(prev_close, curr_open)
            )
        
        # Bearish Engulfing: previous bullish, current bearish and engulfs previous
        elif (prev_close > prev_open and  # Previous bullish
              curr_close < curr_open and  # Current bearish
              curr_open > prev_close and  # Current opens above previous close
              curr_close < prev_open):    # Current closes below previous open
            
            confidence = 0.75
            return self._create_pattern(
                "BEARISH_ENGULFING", "REVERSAL", "BEARISH", confidence,
                len(candles) - 2, len(candles) - 1, max(prev_close, curr_open), min(prev_open, curr_close)
            )
        
        return None
    
    def _detect_harami(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect bullish or bearish harami pattern"""
        if len(candles) < 2:
            return None
        
        prev_candle = candles[0]
        curr_candle = candles[1]
        
        prev_open = float(prev_candle.get("open", 0))
        prev_close = float(prev_candle.get("close", 0))
        curr_open = float(curr_candle.get("open", 0))
        curr_close = float(curr_candle.get("close", 0))
        
        if not all([prev_open, prev_close, curr_open, curr_close]):
            return None
        
        prev_body_size = abs(prev_close - prev_open)
        curr_body_size = abs(curr_close - curr_open)
        
        # Check if current candle body is contained within previous candle body
        if (curr_open > min(prev_open, prev_close) and 
            curr_open < max(prev_open, prev_close) and
            curr_close > min(prev_open, prev_close) and
            curr_close < max(prev_open, prev_close) and
            curr_body_size < prev_body_size * 0.5):  # Current body significantly smaller
            
            # Bullish Harami: previous bearish, current bullish
            if prev_close < prev_open and curr_close > curr_open:
                confidence = 0.70
                return self._create_pattern(
                    "BULLISH_HARAMI", "REVERSAL", "BULLISH", confidence,
                    len(candles) - 2, len(candles) - 1, 
                    max(prev_open, prev_close, curr_open, curr_close),
                    min(prev_open, prev_close, curr_open, curr_close)
                )
            
            # Bearish Harami: previous bullish, current bearish
            elif prev_close > prev_open and curr_close < curr_open:
                confidence = 0.70
                return self._create_pattern(
                    "BEARISH_HARAMI", "REVERSAL", "BEARISH", confidence,
                    len(candles) - 2, len(candles) - 1,
                    max(prev_open, prev_close, curr_open, curr_close),
                    min(prev_open, prev_close, curr_open, curr_close)
                )
        
        return None
    
    def _detect_single_candlestick(self, candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect single candlestick patterns"""
        open_price = float(candle.get("open", 0))
        high_price = float(candle.get("high", 0))
        low_price = float(candle.get("low", 0))
        close_price = float(candle.get("close", 0))
        
        if not all([open_price, high_price, low_price, close_price]):
            return None
        
        body_size = abs(close_price - open_price)
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price
        total_range = high_price - low_price
        
        if total_range == 0:
            return None
        
        # Hammer: small body at top, long lower wick
        if (body_size / total_range < 0.3 and  # Small body
            lower_wick / total_range > 0.6 and  # Long lower wick
            upper_wick / total_range < 0.1):    # Small upper wick
            
            confidence = 0.70
            return self._create_pattern(
                "HAMMER", "REVERSAL", "BULLISH", confidence,
                0, 0, high_price, low_price
            )
        
        # Shooting Star: small body at bottom, long upper wick
        elif (body_size / total_range < 0.3 and  # Small body
              upper_wick / total_range > 0.6 and  # Long upper wick
              lower_wick / total_range < 0.1):    # Small lower wick
            
            confidence = 0.70
            return self._create_pattern(
                "SHOOTING_STAR", "REVERSAL", "BEARISH", confidence,
                0, 0, high_price, low_price
            )
        
        # Doji: very small body
        elif body_size / total_range < 0.1:
            confidence = 0.60
            return self._create_pattern(
                "DOJI", "REVERSAL", "NEUTRAL", confidence,
                0, 0, high_price, low_price
            )
        
        return None
