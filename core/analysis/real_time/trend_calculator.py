#!/usr/bin/env python3
"""
Trend Calculator Module
Simple, working trend calculation
"""

from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger


class TrendCalculator:
    """Simple trend calculation system"""
    
    def __init__(self):
        logger.info("📈 Trend Calculator initialized - Simple working logic")
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m", strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Calculate real-time trend using strategy-specific parameters with explicit trend types
        Returns BOTH short-term (3 candles/15min) and medium-term (6 candles/30min) trends
        """
        try:
            if len(candles) < 3:  # More reactive - need only 3 candles minimum
                return {
                    "trend": "SIDEWAYS", 
                    "trend_short": "SIDEWAYS",
                    "trend_medium": "SIDEWAYS",
                    "trend_type": "NO_DATA", 
                    "strength": 0, 
                    "direction": 0, 
                    "confidence": 0
                }
            
            # Get strategy-specific trend parameters
            trend_params = self._get_strategy_trend_params(strategy_name)
            num_candles = min(trend_params["num_candles"], len(candles))
            recent_closes = [candle["close"] for candle in candles[-num_candles:]]
            
            # DUAL-TIMEFRAME TREND ANALYSIS
            # 1. Short-term (3 candles / 15 min) - Momentum confirmation
            short_closes = [float(candle["close"]) for candle in candles[-3:]]
            short_change_pct = ((short_closes[-1] - short_closes[0]) / short_closes[0]) * 100
            
            # 2. Medium-term (24 candles / 2 hours) - Intraday trend direction
            medium_candles = candles[-24:] if len(candles) >= 24 else candles
            medium_closes = [float(candle["close"]) for candle in medium_candles]
            medium_change_pct = ((medium_closes[-1] - medium_closes[0]) / medium_closes[0]) * 100
            
            # For backward compatibility
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
            
            # CLASSIFY EACH TIMEFRAME INDEPENDENTLY
            # Thresholds for classification
            short_thresholds = {"strong": 0.3, "moderate": 0.15, "weak": 0.05}
            medium_thresholds = {"strong": 1.0, "moderate": 0.5, "weak": 0.2}  # 2-hour trend needs bigger moves
            
            # Classify short-term trend (15 min)
            trend_short = self._classify_trend(short_change_pct, short_thresholds)
            
            # Classify medium-term trend (2 hours)
            trend_medium = self._classify_trend(medium_change_pct, medium_thresholds)
            
            # Primary trend (for backward compatibility) - use medium-term
            trend = trend_medium
            trend_pct = medium_change_pct
            direction = 1 if trend_pct > 0 else -1 if trend_pct < 0 else 0
            
            return {
                # Primary trend (medium-term for backward compatibility)
                "trend": trend,
                "direction": direction,
                "strength": round(strength, 3),
                "momentum": round(momentum, 6),
                "price_change": round(trend_pct, 3),
                
                # Dual-timeframe trends for prediction
                "trend_short": trend_short,           # 15 min - momentum confirmation
                "trend_medium": trend_medium,         # 2 hours - intraday direction
                "short_change_pct": round(short_change_pct, 3),
                "medium_change_pct": round(medium_change_pct, 3),
                
                # Metadata
                "timeframe": timeframe,
                "strategy": strategy_name,
                "num_candles_used": num_candles,
                "data_source": f"realtime_{strategy_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return {"trend": "SIDEWAYS", "trend_timeframe": "NO_DATA", "strength": 0, "direction": 0, "confidence": 0}
    
    def _classify_trend(self, change_pct: float, thresholds: Dict[str, float]) -> str:
        """Classify trend based on percentage change and thresholds"""
        abs_change = abs(change_pct)
        
        if abs_change > thresholds["strong"]:
            return "STRONG_UPTREND" if change_pct > 0 else "STRONG_DOWNTREND"
        elif abs_change > thresholds["moderate"]:
            return "UPTREND" if change_pct > 0 else "DOWNTREND"
        elif abs_change > thresholds["weak"]:
            return "WEAK_UPTREND" if change_pct > 0 else "WEAK_DOWNTREND"
        else:
            return "SIDEWAYS"
    
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


# Singleton pattern implementation
_global_trend_calculator = None

def get_global_trend_calculator() -> TrendCalculator:
    """Get the global TrendCalculator singleton instance"""
    global _global_trend_calculator
    if _global_trend_calculator is None:
        _global_trend_calculator = TrendCalculator()
    return _global_trend_calculator

# Backward compatibility - lazy initialization
def global_trend_calculator():
    return get_global_trend_calculator()
