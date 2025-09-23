#!/usr/bin/env python3
"""
Trend Calculator Module
Simple, working trend calculation
"""

# import numpy as np  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger


class TrendCalculator:
    """Simple trend calculation system"""
    
    def __init__(self):
        logger.info("📈 Trend Calculator initialized - Simple working logic")
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m", strategy_name: str = "standard") -> Dict[str, Any]:
        """Calculate real-time trend using strategy-specific parameters with explicit trend types"""
        try:
            if len(candles) < 3:  # More reactive - need only 3 candles minimum
                return {"trend": "SIDEWAYS", "trend_type": "NO_DATA", "strength": 0, "direction": 0, "confidence": 0}
            
            # Get strategy-specific trend parameters
            trend_params = self._get_strategy_trend_params(strategy_name)
            num_candles = min(trend_params["num_candles"], len(candles))
            recent_closes = [candle["close"] for candle in candles[-num_candles:]]
            
            # REAL-TIME: Calculate multiple timeframe trends for better detection
            # 1. Ultra-short term (last 2-3 candles) - immediate reaction
            ultra_short_closes = [candle["close"] for candle in candles[-3:]]
            ultra_short_change_pct = ((ultra_short_closes[-1] - ultra_short_closes[0]) / ultra_short_closes[0]) * 100
            
            # 2. Short-term trend (last 5 candles) - recent momentum
            short_closes = [candle["close"] for candle in candles[-5:]]
            short_first = short_closes[0]
            short_last = short_closes[-1]
            short_change_pct = ((short_last - short_first) / short_first) * 100
            
            # 3. Medium-term trend (strategy-specific candles) - main trend
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            # Calculate trend consistency
            up_moves = 0
            down_moves = 0
            total_moves = 0
            
            for i in range(1, len(recent_closes)):
                if recent_closes[i] > recent_closes[i-1]:
                    up_moves += 1
                    total_moves += 1
                elif recent_closes[i] < recent_closes[i-1]:
                    down_moves += 1
                    total_moves += 1
            
            if total_moves == 0:
                strength = 0
            else:
                dominant_moves = max(up_moves, down_moves)
                strength = dominant_moves / total_moves
            
            # Calculate momentum
            momentum = self._calculate_momentum(recent_closes)
            
            # REAL-TIME TREND DETECTION: Multi-timeframe analysis with explicit trend types
            ultra_short_abs = abs(ultra_short_change_pct)
            short_term_abs = abs(short_change_pct)
            medium_term_abs = abs(price_change_pct)
            
            # Pattern-based trend detection (more sensitive)
            consecutive_green = 0
            consecutive_red = 0
            max_consecutive_green = 0
            max_consecutive_red = 0
            current_consecutive = 0
            
            for i in range(1, len(recent_closes)):
                if recent_closes[i] > recent_closes[i-1]:
                    consecutive_green += 1
                    consecutive_red = 0
                    max_consecutive_green = max(max_consecutive_green, consecutive_green)
                elif recent_closes[i] < recent_closes[i-1]:
                    consecutive_red += 1
                    consecutive_green = 0
                    max_consecutive_red = max(max_consecutive_red, consecutive_red)
                else:
                    consecutive_green = 0
                    consecutive_red = 0
            
            # REAL-TIME: Determine trend priority (ultra-short gets highest priority for immediate reaction)
            trend_pct = 0
            trend_type = "SIDEWAYS"
            trend_source = "none"
            
            # Priority 1: Ultra-short term (immediate reaction) - more reasonable thresholds
            if ultra_short_abs > 0.1:  # 0.1% threshold for immediate reaction (was 0.01%)
                trend_pct = ultra_short_change_pct
                trend_type = "IMMEDIATE"
                trend_source = "ultra_short"
            # Priority 2: Short-term momentum (recent action)
            elif short_term_abs > 0.2:  # 0.2% threshold for short-term (was 0.02%)
                trend_pct = short_change_pct
                trend_type = "SHORT_TERM"
                trend_source = "short_term"
            # Priority 3: Medium-term trend (sustained move)
            elif medium_term_abs > 0.3:  # 0.3% threshold for medium-term (was 0.03%)
                trend_pct = price_change_pct
                trend_type = "MEDIUM_TERM"
                trend_source = "medium_term"
            # Priority 4: Pattern-based detection (consecutive candles) - more stable
            elif max_consecutive_green >= 3 or max_consecutive_red >= 3:  # Increased to 3 candles for stability
                if max_consecutive_green >= max_consecutive_red:
                    trend_pct = 0.15  # Small positive trend (was 0.015 - 10x more stable)
                    trend_type = "PATTERN_BULLISH"
                    trend_source = "pattern"
                else:
                    trend_pct = -0.15  # Small negative trend (was -0.015 - 10x more stable)
                    trend_type = "PATTERN_BEARISH"
                    trend_source = "pattern"
            else:
                trend_pct = price_change_pct
                trend_type = "SIDEWAYS"
                trend_source = "medium_term"
            
            # Apply strategy-specific trend classification (basic classification)
            thresholds = trend_params["thresholds"]
            direction = 1 if trend_pct > 0 else -1 if trend_pct < 0 else 0
            
            # Basic trend classification
            if abs(trend_pct) > thresholds["strong"]:  # Strong trend
                if trend_pct > thresholds["strong"]:
                    trend = "STRONG_UPTREND"
                else:
                    trend = "STRONG_DOWNTREND"
            elif abs(trend_pct) > thresholds["moderate"]:  # Moderate trend
                if trend_pct > thresholds["moderate"]:
                    trend = "UPTREND"
                else:
                    trend = "DOWNTREND"
            elif abs(trend_pct) > thresholds["weak"]:  # Weak trend
                if trend_pct > thresholds["weak"]:
                    trend = "WEAK_UPTREND"
                else:
                    trend = "WEAK_DOWNTREND"
            else:
                trend = "SIDEWAYS"
            
            return {
                "trend": trend,
                "trend_timeframe": trend_type,  # What type of trend (IMMEDIATE, SHORT_TERM, MEDIUM_TERM, etc.)
                "trend_source": trend_source,
                "strength": round(strength, 3),
                "direction": direction,
                "momentum": round(momentum, 6),
                "acceleration": 0.0,
                "price_change": round(price_change_pct, 3),
                "ultra_short_change": round(ultra_short_change_pct, 3),
                "short_term_change": round(short_change_pct, 3),
                "medium_term_change": round(price_change_pct, 3),
                "volume_confirmation": False,
                "timeframe": timeframe,
                "strategy": strategy_name,
                "num_candles_used": num_candles,
                "consecutive_green": max_consecutive_green,
                "consecutive_red": max_consecutive_red,
                "data_source": f"realtime_{strategy_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return {"trend": "SIDEWAYS", "trend_timeframe": "NO_DATA", "strength": 0, "direction": 0, "confidence": 0}
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum"""
        if len(prices) < 2:
            return 0.0
        
        # Simple momentum calculation
        if len(prices) >= 3:
            momentum_1 = (prices[-1] - prices[-2]) / prices[-2]
            momentum_2 = (prices[-2] - prices[-3]) / prices[-3]
            momentum = (momentum_1 * 0.6) + (momentum_2 * 0.4)
        else:
            momentum = (prices[-1] - prices[-2]) / prices[-2]
        
        return momentum
    
    def _check_volume_confirmation(self, candles: List[Dict]) -> bool:
        """Check volume confirmation (simplified)"""
        return True  # Simplified for now
    
    def _get_strategy_trend_params(self, strategy_name: str) -> Dict[str, Any]:
        """Get strategy-specific trend calculation parameters"""
        strategy_params = {
            "standard": {
                "num_candles": 6,   # 30 minutes for 5m candles - more stable
                "thresholds": {
                    "strong": 0.5,    # 0.5% for strong trends (was 0.05% - 10x more stable)
                    "moderate": 0.2,  # 0.2% for moderate trends (was 0.02% - 10x more stable)
                    "weak": 0.08      # 0.08% for weak trends (was 0.008% - 10x more stable)
                }
            },
            "low_volatility_range": {
                "num_candles": 4,   # 20 minutes - more stable for range detection
                "thresholds": {
                    "strong": 0.3,    # 0.3% for strong trends (was 0.05% - 6x more stable)
                    "moderate": 0.15,  # 0.15% for moderate trends (was 0.02% - 7.5x more stable)
                    "weak": 0.05      # 0.05% for weak trends (was 0.008% - 6x more stable)
                }
            },
            "high_volatility": {
                "num_candles": 8,   # 40 minutes - appropriate for high volatility
                "thresholds": {
                    "strong": 1.0,    # 1.0% for strong trends (was 0.3% - 3x more stable)
                    "moderate": 0.5,  # 0.5% for moderate trends (was 0.12% - 4x more stable)
                    "weak": 0.2       # 0.2% for weak trends (was 0.04% - 5x more stable)
                }
            },
            "spike_hunting": {
                "num_candles": 3,   # 15 minutes - more stable for spike detection
                "thresholds": {
                    "strong": 0.8,    # 0.8% for strong trends (was 0.1% - 8x more stable)
                    "moderate": 0.4,  # 0.4% for moderate trends (was 0.05% - 8x more stable)
                    "weak": 0.15      # 0.15% for weak trends (was 0.02% - 7.5x more stable)
                }
            },
            "trend_following": {
                "num_candles": 8,   # 40 minutes - more stable for trend following
                "thresholds": {
                    "strong": 0.6,    # 0.6% for strong trends (was 0.08% - 7.5x more stable)
                    "moderate": 0.3,  # 0.3% for moderate trends (was 0.03% - 10x more stable)
                    "weak": 0.12      # 0.12% for weak trends (was 0.015% - 8x more stable)
                }
            }
        }
        
        return strategy_params.get(strategy_name, strategy_params["standard"])


# Global instance for easy access
global_trend_calculator = TrendCalculator()
