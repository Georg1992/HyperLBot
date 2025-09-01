#!/usr/bin/env python3
"""
Trend Calculator Module
Centralized trend calculations following established calculator pattern
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class TrendCalculator:
    """Centralized trend calculation system (follows VolatilityCalculator pattern)"""
    
    def __init__(self):
        logger.info("📈 Trend Calculator initialized")
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m") -> Dict[str, Any]:
        """Calculate trend with multi-timeframe analysis (core calculation method)"""
        try:
            if not candles or len(candles) < 5:
                return self._get_default_trend()
            
            # Extract price data
            closes = [float(candle.get('close', 0)) for candle in candles]
            highs = [float(candle.get('high', candle.get('close', 0))) for candle in candles]
            lows = [float(candle.get('low', candle.get('close', 0))) for candle in candles]
            
            if not closes or closes[-1] == 0:
                return self._get_default_trend()
            
            # Calculate trend metrics
            trend_direction = self._calculate_trend_direction(closes)
            trend_strength = self._calculate_trend_strength(closes, highs, lows)
            price_momentum = self._calculate_price_momentum(closes)
            
            # Determine overall trend classification
            overall_trend = self._classify_trend(trend_direction, trend_strength, price_momentum)
            
            return {
                "trend": overall_trend,
                "direction": trend_direction,
                "strength": round(trend_strength, 3),
                "momentum": round(price_momentum, 6),
                "price_change": round((closes[-1] - closes[0]) / closes[0] * 100, 3),
                "timeframe": timeframe,
                "candles_analyzed": len(candles),
                "data_source": "trend_calculator"
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return self._get_default_trend()
    
    def _calculate_trend_direction(self, closes: List[float]) -> str:
        """Calculate primary trend direction"""
        try:
            if len(closes) < 3:
                return "NEUTRAL"
            
            # Simple trend analysis using first and last prices
            start_price = closes[0]
            end_price = closes[-1]
            price_change_pct = (end_price - start_price) / start_price
            
            # Calculate linear regression slope for more accuracy
            if len(closes) >= 5:
                x = list(range(len(closes)))
                slope = np.polyfit(x, closes, 1)[0]
                
                # Combine price change and slope for direction
                if slope > 0 and price_change_pct > 0.002:  # 0.2% threshold
                    return "UP"
                elif slope < 0 and price_change_pct < -0.002:  # -0.2% threshold
                    return "DOWN"
                else:
                    return "SIDEWAYS"
            else:
                # Simple direction for limited data
                if price_change_pct > 0.005:  # 0.5%
                    return "UP"
                elif price_change_pct < -0.005:  # -0.5%
                    return "DOWN"
                else:
                    return "SIDEWAYS"
                    
        except Exception as e:
            logger.warning(f"Trend direction calculation failed: {e}")
            return "NEUTRAL"
    
    def _calculate_trend_strength(self, closes: List[float], highs: List[float], lows: List[float]) -> float:
        """Calculate trend strength (0.0 to 1.0)"""
        try:
            if len(closes) < 3:
                return 0.5
            
            # Calculate price range and consistency
            price_range = max(closes) - min(closes)
            avg_price = sum(closes) / len(closes)
            
            if avg_price == 0:
                return 0.5
            
            # Range-based strength
            range_strength = min(1.0, (price_range / avg_price) * 50)  # Normalize range
            
            # Consistency-based strength (how consistent is the direction)
            directional_changes = 0
            for i in range(1, len(closes)):
                prev_direction = 1 if closes[i-1] > closes[i-2] else -1 if i > 1 else 1
                curr_direction = 1 if closes[i] > closes[i-1] else -1
                if prev_direction != curr_direction:
                    directional_changes += 1
            
            consistency = 1.0 - (directional_changes / (len(closes) - 1)) if len(closes) > 1 else 1.0
            
            # Combine range and consistency
            strength = (range_strength * 0.6) + (consistency * 0.4)
            return max(0.1, min(1.0, strength))
            
        except Exception as e:
            logger.warning(f"Trend strength calculation failed: {e}")
            return 0.5
    
    def _calculate_price_momentum(self, closes: List[float]) -> float:
        """Calculate price momentum"""
        try:
            if len(closes) < 3:
                return 0.0
            
            # Calculate momentum as rate of price change acceleration
            recent_change = closes[-1] - closes[-2] if len(closes) >= 2 else 0
            previous_change = closes[-2] - closes[-3] if len(closes) >= 3 else 0
            
            if abs(previous_change) < 1e-10:  # Avoid division by very small numbers
                return 0.0
            
            momentum = (recent_change - previous_change) / closes[-1] if closes[-1] > 0 else 0.0
            return momentum
            
        except Exception as e:
            logger.warning(f"Price momentum calculation failed: {e}")
            return 0.0
    
    def _classify_trend(self, direction: str, strength: float, momentum: float) -> str:
        """Classify overall trend based on direction, strength, and momentum"""
        try:
            # Strong trend thresholds
            strong_threshold = 0.7
            weak_threshold = 0.3
            
            if direction == "UP":
                if strength > strong_threshold:
                    return "STRONG_UPTREND"
                elif strength > weak_threshold:
                    return "UPTREND"
                else:
                    return "WEAK_UPTREND"
            elif direction == "DOWN":
                if strength > strong_threshold:
                    return "STRONG_DOWNTREND"
                elif strength > weak_threshold:
                    return "DOWNTREND"
                else:
                    return "WEAK_DOWNTREND"
            else:  # SIDEWAYS or NEUTRAL
                if abs(momentum) > 0.001:
                    return "SIDEWAYS"
                else:
                    return "NEUTRAL"
                    
        except Exception as e:
            logger.warning(f"Trend classification failed: {e}")
            return "NEUTRAL"
    
    def _get_default_trend(self) -> Dict[str, Any]:
        """Get default trend data when calculation fails"""
        return {
            "trend": "NEUTRAL",
            "direction": "NEUTRAL",
            "strength": 0.5,
            "momentum": 0.0,
            "price_change": 0.0,
            "timeframe": "unknown",
            "candles_analyzed": 0,
            "data_source": "default_fallback"
        }