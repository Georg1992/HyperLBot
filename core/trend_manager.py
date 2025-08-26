#!/usr/bin/env python3
"""
Advanced Trend Manager
Replaces the basic trend calculation with sophisticated multi-timeframe trend recognition
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger

class TrendManager:
    """Advanced trend manager with multi-timeframe analysis and reversal detection"""
    
    def __init__(self):
        # Cache for trend calculations
        self._trend_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 30  # 30 seconds cache for trend data
        
        logger.info("📈 Trend Manager initialized - Advanced trend recognition system")
    
    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self._trend_cache:
            timestamp = self._cache_timestamps.get(key, 0)
            if time.time() - timestamp < self._cache_duration:
                return self._trend_cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self._trend_cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def calculate_trend(self, candles: List[Dict], periods: int = 5) -> Dict[str, Any]:
        """Calculate trend with advanced analysis"""
        cache_key = f"trend_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods:
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
            
            # Get recent closes
            recent_closes = [candle["close"] for candle in candles[-periods:]]
            
            # Calculate basic trend metrics
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            # Calculate trend consistency
            up_moves = 0
            down_moves = 0
            
            for i in range(1, len(recent_closes)):
                if recent_closes[i] > recent_closes[i-1]:
                    up_moves += 1
                elif recent_closes[i] < recent_closes[i-1]:
                    down_moves += 1
            
            total_moves = up_moves + down_moves
            if total_moves == 0:
                strength = 0
            else:
                strength = max(up_moves, down_moves) / total_moves
            
            # Calculate momentum
            momentum = self._calculate_momentum(recent_closes)
            
            # Calculate volume confirmation (if available)
            volume_confirmation = self._check_volume_confirmation(candles[-periods:])
            
            # Determine trend with enhanced logic
            if price_change_pct > 0.5 and strength > 0.6 and momentum > 0:
                trend = "UPTREND"
                direction = 1
            elif price_change_pct < -0.5 and strength > 0.6 and momentum < 0:
                trend = "DOWNTREND"
                direction = -1
            elif abs(price_change_pct) < 0.2:
                trend = "SIDEWAYS"
                direction = 0
            else:
                # Weak trend
                if price_change_pct > 0:
                    trend = "WEAK_UPTREND"
                    direction = 1
                else:
                    trend = "WEAK_DOWNTREND"
                    direction = -1
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(
                strength, momentum, volume_confirmation, abs(price_change_pct)
            )
            
            result = {
                "trend": trend,
                "strength": round(strength, 3),
                "direction": direction,
                "price_change_pct": round(price_change_pct, 3),
                "momentum": round(momentum, 3),
                "volume_confirmed": volume_confirmation,
                "confidence": round(confidence, 3),
                "up_moves": up_moves,
                "down_moves": down_moves,
                "periods_analyzed": periods
            }
            
            self._cache_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum"""
        if len(prices) < 3:
            return 0.0
        
        # Calculate rate of change
        recent_change = (prices[-1] - prices[-2]) / prices[-2]
        previous_change = (prices[-2] - prices[-3]) / prices[-3]
        
        # Momentum is acceleration (change in rate of change)
        momentum = recent_change - previous_change
        return momentum
    
    def _check_volume_confirmation(self, candles: List[Dict]) -> bool:
        """Check if volume confirms the trend"""
        if len(candles) < 3:
            return False
        
        # Get recent volumes
        volumes = [candle.get("volume", 0) for candle in candles]
        
        # Check if recent volume is above average
        if len(volumes) >= 3:
            recent_volume = volumes[-1]
            avg_volume = sum(volumes[:-1]) / (len(volumes) - 1)
            
            # Volume confirms trend if recent volume > 80% of average
            return recent_volume > avg_volume * 0.8
        
        return False
    
    def _calculate_confidence_score(self, strength: float, momentum: float, 
                                  volume_confirmed: bool, price_change: float) -> float:
        """Calculate confidence score for trend"""
        confidence = 0.0
        
        # Base confidence from strength
        confidence += strength * 0.4
        
        # Momentum contribution
        momentum_score = min(abs(momentum) * 10, 1.0)
        confidence += momentum_score * 0.3
        
        # Volume confirmation
        if volume_confirmed:
            confidence += 0.2
        
        # Price change contribution
        price_score = min(price_change / 2.0, 1.0)  # Normalize to 0-1
        confidence += price_score * 0.1
        
        return min(confidence, 1.0)
    
    def detect_trend_reversal(self, candles: List[Dict], periods: int = 10) -> Dict[str, Any]:
        """Detect early signs of trend reversal"""
        try:
            if len(candles) < periods:
                return {"reversal_probability": 0, "signals": []}
            
            recent_candles = candles[-periods:]
            signals = []
            reversal_score = 0.0
            
            # 1. Check for divergence (price vs RSI)
            divergence = self._check_divergence(recent_candles)
            if divergence["detected"]:
                signals.append(f"Divergence: {divergence['type']}")
                reversal_score += 0.3
            
            # 2. Check momentum weakening
            momentum_weakening = self._check_momentum_weakening(recent_candles)
            if momentum_weakening:
                signals.append("Momentum weakening")
                reversal_score += 0.25
            
            # 3. Check volume decline
            volume_decline = self._check_volume_decline(recent_candles)
            if volume_decline:
                signals.append("Volume decline")
                reversal_score += 0.2
            
            # 4. Check support/resistance levels
            sr_test = self._check_support_resistance_test(recent_candles)
            if sr_test["testing"]:
                signals.append(f"Testing {sr_test['level_type']}")
                reversal_score += 0.25
            
            return {
                "reversal_probability": min(reversal_score, 1.0),
                "signals": signals,
                "confidence": len(signals) * 0.2
            }
            
        except Exception as e:
            logger.error(f"❌ Trend reversal detection failed: {e}")
            return {"reversal_probability": 0, "signals": []}
    
    def _check_divergence(self, candles: List[Dict]) -> Dict[str, Any]:
        """Check for price/RSI divergence"""
        if len(candles) < 6:
            return {"detected": False, "type": None}
        
        # Simple divergence check (price higher highs, RSI lower highs)
        prices = [c["close"] for c in candles[-6:]]
        highs = []
        
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                highs.append((i, prices[i]))
        
        if len(highs) >= 2:
            # Check if highs are decreasing
            if highs[-1][1] < highs[-2][1]:
                return {"detected": True, "type": "bearish_divergence"}
        
        return {"detected": False, "type": None}
    
    def _check_momentum_weakening(self, candles: List[Dict]) -> bool:
        """Check if momentum is weakening"""
        if len(candles) < 5:
            return False
        
        prices = [c["close"] for c in candles[-5:]]
        
        # Calculate recent momentum changes
        momentum_1 = (prices[-1] - prices[-2]) / prices[-2]
        momentum_2 = (prices[-2] - prices[-3]) / prices[-3]
        momentum_3 = (prices[-3] - prices[-4]) / prices[-4]
        
        # Check if momentum is decreasing
        return abs(momentum_1) < abs(momentum_2) < abs(momentum_3)
    
    def _check_volume_decline(self, candles: List[Dict]) -> bool:
        """Check if volume is declining"""
        if len(candles) < 4:
            return False
        
        volumes = [c.get("volume", 0) for c in candles[-4:]]
        
        # Check if recent volume is declining
        return volumes[-1] < volumes[-2] < volumes[-3]
    
    def _check_support_resistance_test(self, candles: List[Dict]) -> Dict[str, Any]:
        """Check if price is testing support/resistance levels"""
        if len(candles) < 3:
            return {"testing": False, "level_type": None}
        
        recent_high = max(c["high"] for c in candles[-10:])
        recent_low = min(c["low"] for c in candles[-10:])
        current_price = candles[-1]["close"]
        
        # Check if price is near recent high (resistance)
        if abs(current_price - recent_high) / recent_high < 0.002:  # Within 0.2%
            return {"testing": True, "level_type": "resistance", "level": recent_high}
        
        # Check if price is near recent low (support)
        if abs(current_price - recent_low) / recent_low < 0.002:  # Within 0.2%
            return {"testing": True, "level_type": "support", "level": recent_low}
        
        return {"testing": False, "level_type": None}
    
    def get_multi_timeframe_trend(self, candles_1m: List[Dict], candles_5m: List[Dict], 
                                 candles_1h: List[Dict]) -> Dict[str, Any]:
        """Get comprehensive multi-timeframe trend analysis"""
        try:
            # Calculate trends for each timeframe
            trend_1m = self.calculate_trend(candles_1m, 5)  # 5 minutes
            trend_5m = self.calculate_trend(candles_5m, 6)  # 30 minutes
            trend_1h = self.calculate_trend(candles_1h, 12)  # 12 hours
            
            # Calculate alignment score
            alignment_score = self._calculate_alignment_score(trend_1m, trend_5m, trend_1h)
            
            # Determine overall trend
            overall_trend = self._determine_overall_trend(trend_1m, trend_5m, trend_1h, alignment_score)
            
            # Check for reversals
            reversal_analysis = self.detect_trend_reversal(candles_5m, 10)
            
            return {
                "overall_trend": overall_trend,
                "alignment_score": alignment_score,
                "timeframes": {
                    "1m": trend_1m,
                    "5m": trend_5m,
                    "1h": trend_1h
                },
                "reversal_analysis": reversal_analysis,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe trend analysis failed: {e}")
            return {
                "overall_trend": "UNKNOWN",
                "alignment_score": 0,
                "timeframes": {},
                "reversal_analysis": {"reversal_probability": 0, "signals": []}
            }
    
    def _calculate_alignment_score(self, trend_1m: Dict, trend_5m: Dict, trend_1h: Dict) -> float:
        """Calculate how well trends align across timeframes"""
        alignment_score = 0.0
        
        # Short-term alignment (1m + 5m)
        if trend_1m["direction"] == trend_5m["direction"]:
            alignment_score += 0.4
        
        # Medium-term alignment (5m + 1h)
        if trend_5m["direction"] == trend_1h["direction"]:
            alignment_score += 0.3
        
        # Long-term alignment (1m + 1h)
        if trend_1m["direction"] == trend_1h["direction"]:
            alignment_score += 0.3
        
        return alignment_score
    
    def _determine_overall_trend(self, trend_1m: Dict, trend_5m: Dict, 
                                trend_1h: Dict, alignment_score: float) -> str:
        """Determine overall trend based on multi-timeframe analysis"""
        
        # If strong alignment, follow the majority
        if alignment_score > 0.7:
            directions = [trend_1m["direction"], trend_5m["direction"], trend_1h["direction"]]
            up_count = sum(1 for d in directions if d > 0)
            down_count = sum(1 for d in directions if d < 0)
            
            if up_count > down_count:
                return "STRONG_UPTREND"
            elif down_count > up_count:
                return "STRONG_DOWNTREND"
            else:
                return "MIXED"
        
        # If weak alignment, prioritize shorter timeframes
        elif alignment_score > 0.4:
            if trend_1m["direction"] == trend_5m["direction"]:
                if trend_1m["direction"] > 0:
                    return "UPTREND"
                else:
                    return "DOWNTREND"
            else:
                return "MIXED"
        
        # No alignment - sideways
        else:
            return "SIDEWAYS"

# Global instance
trend_manager = TrendManager()
