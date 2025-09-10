#!/usr/bin/env python3
"""
Trend Calculator Module
Simple, working trend calculation
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class TrendCalculator:
    """Simple trend calculation system"""
    
    def __init__(self):
        logger.info("📈 Trend Calculator initialized - Simple working logic")
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m", strategy_name: str = "standard") -> Dict[str, Any]:
        """Calculate trend using strategy-specific parameters"""
        try:
            if len(candles) < 5:
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
            
            # Get strategy-specific trend parameters
            trend_params = self._get_strategy_trend_params(strategy_name)
            num_candles = min(trend_params["num_candles"], len(candles))
            recent_closes = [candle["close"] for candle in candles[-num_candles:]]
            
            # Calculate basic trend metrics
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            # Also calculate short-term trend (last 5 candles) for comparison
            short_closes = [candle["close"] for candle in candles[-5:]]
            short_first = short_closes[0]
            short_last = short_closes[-1]
            short_change_pct = ((short_last - short_first) / short_first) * 100
            
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
            
            # Enhanced trend determination using both long-term and short-term trends
            # Use the more significant trend (long-term for sustained moves, short-term for recent changes)
            long_term_abs = abs(price_change_pct)
            short_term_abs = abs(short_change_pct)
            
            # Determine which trend to use (prefer long-term for sustained moves)
            if long_term_abs > 0.1:  # Long-term trend is significant
                use_long_term = True
                trend_pct = price_change_pct
            elif short_term_abs > 0.05:  # Short-term trend is significant
                use_long_term = False
                trend_pct = short_change_pct
            else:
                # Neither is significant, use long-term for consistency
                use_long_term = True
                trend_pct = price_change_pct
            
            # Apply strategy-specific trend classification
            thresholds = trend_params["thresholds"]
            if abs(trend_pct) > thresholds["strong"]:  # Strong trend
                if trend_pct > thresholds["strong"]:
                    trend = "STRONG_UPTREND"
                    direction = 1
                else:
                    trend = "STRONG_DOWNTREND"
                    direction = -1
            elif abs(trend_pct) > thresholds["moderate"]:  # Moderate trend
                if trend_pct > thresholds["moderate"]:
                    trend = "UPTREND"
                    direction = 1
                else:
                    trend = "DOWNTREND"
                    direction = -1
            elif abs(trend_pct) > thresholds["weak"]:  # Weak trend
                if trend_pct > thresholds["weak"]:
                    trend = "WEAK_UPTREND"
                    direction = 1
                else:
                    trend = "WEAK_DOWNTREND"
                    direction = -1
            else:
                trend = "SIDEWAYS"
                direction = 0
            
            return {
                "trend": trend,
                "strength": round(strength, 3),
                "direction": direction,
                "momentum": round(momentum, 6),
                "acceleration": 0.0,
                "price_change": round(price_change_pct, 3),
                "volume_confirmation": False,
                "timeframe": timeframe,
                "strategy": strategy_name,
                "num_candles_used": num_candles,
                "data_source": f"strategy_optimized_{strategy_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
    
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
                "num_candles": 15,  # 75 minutes for 5m candles
                "thresholds": {
                    "strong": 0.2,    # 0.2% for strong trends
                    "moderate": 0.08,  # 0.08% for moderate trends
                    "weak": 0.02       # 0.02% for weak trends
                }
            },
            "low_volatility_range": {
                "num_candles": 8,   # 40 minutes - shorter for range detection
                "thresholds": {
                    "strong": 0.1,    # 0.1% for strong trends (more sensitive)
                    "moderate": 0.04,  # 0.04% for moderate trends
                    "weak": 0.01       # 0.01% for weak trends
                }
            },
            "high_volatility": {
                "num_candles": 20,  # 100 minutes - longer for trend confirmation
                "thresholds": {
                    "strong": 0.4,    # 0.4% for strong trends (less sensitive)
                    "moderate": 0.15,  # 0.15% for moderate trends
                    "weak": 0.05       # 0.05% for weak trends
                }
            },
            "spike_hunting": {
                "num_candles": 12,  # 60 minutes - medium for spike detection
                "thresholds": {
                    "strong": 0.3,    # 0.3% for strong trends
                    "moderate": 0.12,  # 0.12% for moderate trends
                    "weak": 0.03       # 0.03% for weak trends
                }
            },
            "trend_following": {
                "num_candles": 18,  # 90 minutes - longer for trend confirmation
                "thresholds": {
                    "strong": 0.25,   # 0.25% for strong trends
                    "moderate": 0.1,   # 0.1% for moderate trends
                    "weak": 0.03       # 0.03% for weak trends
                }
            }
        }
        
        return strategy_params.get(strategy_name, strategy_params["standard"])


# Global instance for easy access
global_trend_calculator = TrendCalculator()