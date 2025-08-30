#!/usr/bin/env python3
"""
Trend Manager
Replaces the basic trend calculation with multi-timeframe trend recognition
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from collections import deque
import time

class TrendManager:
    """Trend manager with multi-timeframe analysis and reversal detection"""
    
    def __init__(self):
        """Initialize trend manager"""
        self.trend_history = deque(maxlen=100)
        self.reversal_signals = deque(maxlen=50)
        self.last_update = 0
        
        # Add missing cache attributes
        self._trend_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 30  # 30 seconds cache for trend data
        
        logger.info("📈 Trend Manager initialized - Multi-timeframe trend recognition system")
    
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
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m") -> Dict[str, Any]:
        """Calculate trend with multi-timeframe analysis"""
        cache_key = f"trend_{timeframe}_{hash(str(candles[-5:]))}" # Changed to 5 for consistency with other methods
        cached_result = self._get_cached_data(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < 5: # Changed to 5 for consistency with other methods
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
            
            # Get recent closes
            recent_closes = [candle["close"] for candle in candles[-5:]] # Changed to 5 for consistency with other methods
            
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
            volume_confirmation = self._check_volume_confirmation(candles[-5:]) # Changed to 5 for consistency with other methods
            
            # Determine trend with LESS CONSERVATIVE thresholds for Bitcoin
            # Bitcoin 5-min movements: 0.1-0.5% is normal, 0.5%+ is significant
            if price_change_pct > 0.2 and strength > 0.5 and momentum > 0:  # Lowered from 0.5% and 0.6
                trend = "UPTREND"
                direction = 1
            elif price_change_pct < -0.2 and strength > 0.5 and momentum < 0:  # Lowered from -0.5% and 0.6
                trend = "DOWNTREND"
                direction = -1
            elif abs(price_change_pct) < 0.1:  # Lowered from 0.2%
                trend = "SIDEWAYS"
                direction = 0
            else:
                # Weak trend - more permissive for Bitcoin volatility
                if price_change_pct > 0.05 and momentum > 0:  # Lowered threshold
                    trend = "WEAK_UPTREND"
                    direction = 1
                elif price_change_pct < -0.05 and momentum < 0:  # Lowered threshold
                    trend = "WEAK_DOWNTREND"
                    direction = -1
                else:
                    trend = "SIDEWAYS"  # Default when unclear
                    direction = 0
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(
                strength, momentum, volume_confirmation, abs(price_change_pct)
            )
            
            # DEBUG: Log trend calculation details to help identify MIXED trend causes
            logger.info(f"📊 Trend Analysis: {trend} | Price: {price_change_pct:.3f}% | Strength: {strength:.3f} | Momentum: {momentum:.3f}")
            
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
                "periods_analyzed": 5 # Changed to 5 for consistency with other methods
            }
            
            self._cache_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum (rate of change, not acceleration)"""
        if len(prices) < 2:
            return 0.0
        
        # Calculate momentum as average rate of change over recent periods
        if len(prices) >= 3:
            # Use 3-period momentum for better stability
            momentum_1 = (prices[-1] - prices[-2]) / prices[-2]
            momentum_2 = (prices[-2] - prices[-3]) / prices[-3]
            momentum = (momentum_1 + momentum_2) / 2
        else:
            # Single period momentum
            momentum = (prices[-1] - prices[-2]) / prices[-2]
        
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
            trend_1m = self.calculate_trend(candles_1m, "5m")  # 5 minutes
            trend_5m = self.calculate_trend(candles_5m, "6m")  # 30 minutes
            trend_1h = self.calculate_trend(candles_1h, "12h")  # 12 hours
            
            # Calculate alignment score
            alignment_score = self._calculate_alignment_score(trend_1m, trend_5m, trend_1h)
            
            # Determine overall trend
            overall_trend = self._determine_overall_trend(trend_1m, trend_5m, trend_1h, alignment_score)
            
            # DEBUG: Log multi-timeframe analysis to understand MIXED trend frequency
            logger.info(f"📊 Multi-Timeframe Trends: 1m={trend_1m.get('trend', 'N/A')} | 5m={trend_5m.get('trend', 'N/A')} | 1h={trend_1h.get('trend', 'N/A')}")
            logger.info(f"📊 Alignment: {alignment_score:.3f} → Overall: {overall_trend}")
            
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
        """Calculate how well trends align across timeframes - MORE PERMISSIVE for Bitcoin"""
        alignment_score = 0.0
        
        # Short-term alignment (1m + 5m) - most important for Bitcoin trading
        if trend_1m["direction"] == trend_5m["direction"]:
            alignment_score += 0.5  # Increased weight
        elif trend_1m["direction"] * trend_5m["direction"] > 0:  # Same sign (both positive or negative)
            alignment_score += 0.25  # Partial credit for same direction
        
        # Medium-term alignment (5m + 1h)
        if trend_5m["direction"] == trend_1h["direction"]:
            alignment_score += 0.3
        elif trend_5m["direction"] * trend_1h["direction"] > 0:  # Same sign
            alignment_score += 0.15  # Partial credit
        
        # Long-term alignment (1m + 1h) - less critical for Bitcoin 5-min trading
        if trend_1m["direction"] == trend_1h["direction"]:
            alignment_score += 0.2  # Reduced weight
        elif trend_1m["direction"] * trend_1h["direction"] > 0:  # Same sign
            alignment_score += 0.1  # Partial credit
        
        return min(alignment_score, 1.0)  # Cap at 1.0
    
    def _determine_overall_trend(self, trend_1m: Dict, trend_5m: Dict, 
                                trend_1h: Dict, alignment_score: float) -> str:
        """Determine overall trend based on multi-timeframe analysis - LESS MIXED results"""
        
        # PRIORITIZE 5m timeframe for Bitcoin trading (most relevant for bot decisions)
        primary_direction = trend_5m.get("direction", 0)
        primary_strength = trend_5m.get("strength", 0)
        
        # If strong alignment, follow the majority but be less strict about MIXED
        if alignment_score > 0.6:  # Lowered from 0.7
            directions = [trend_1m["direction"], trend_5m["direction"], trend_1h["direction"]]
            up_count = sum(1 for d in directions if d > 0)
            down_count = sum(1 for d in directions if d < 0)
            
            if up_count >= 2:  # 2 out of 3 timeframes agree
                return "STRONG_UPTREND"
            elif down_count >= 2:  # 2 out of 3 timeframes agree  
                return "STRONG_DOWNTREND"
            else:
                # Even with mixed timeframes, follow 5m trend if it's strong
                if primary_strength > 0.6:
                    return "UPTREND" if primary_direction > 0 else "DOWNTREND"
                else:
                    # Follow 5m trend even with mixed timeframes if it shows direction
                    if abs(primary_direction) > 0 and primary_strength > 0.3:
                        return "WEAK_UPTREND" if primary_direction > 0 else "WEAK_DOWNTREND"
                    else:
                        return "SIDEWAYS"  # Avoid MIXED, use SIDEWAYS instead
        
        # If moderate alignment, prioritize 5m and 1m (shorter timeframes for Bitcoin)
        elif alignment_score > 0.3:  # Lowered from 0.4
            if trend_1m["direction"] == trend_5m["direction"] and trend_1m["direction"] != 0:
                strength_avg = (trend_1m.get("strength", 0) + trend_5m.get("strength", 0)) / 2
                if strength_avg > 0.4:  # Lowered from implicit higher threshold
                    return "UPTREND" if trend_1m["direction"] > 0 else "DOWNTREND"
                else:
                    return "WEAK_UPTREND" if trend_1m["direction"] > 0 else "WEAK_DOWNTREND"
            else:
                # Follow the stronger trend instead of defaulting to MIXED
                strongest_trend = max([trend_1m, trend_5m, trend_1h], key=lambda t: t.get("strength", 0))
                if strongest_trend.get("strength", 0) > 0.4:
                    if strongest_trend["direction"] > 0:
                        return "WEAK_UPTREND"
                    elif strongest_trend["direction"] < 0:
                        return "WEAK_DOWNTREND"
                    else:
                        return "SIDEWAYS"
                else:
                    return "SIDEWAYS"
        
        # Low alignment - use 5m trend as primary indicator
        else:
            if primary_strength > 0.3:  # Follow 5m trend if it has some strength
                if primary_direction > 0:
                    return "WEAK_UPTREND"
                elif primary_direction < 0:
                    return "WEAK_DOWNTREND"
                else:
                    return "SIDEWAYS"
            else:
                return "SIDEWAYS"

# Global instance
trend_manager = TrendManager()
