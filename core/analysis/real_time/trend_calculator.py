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
            "scalping": {
                "primary": 3,       # 15 min - quick momentum
                "confirmation": 6,  # 30 min - trend confirmation
                "reaction": 2,      # 10 min - entry timing
                "thresholds": {"strong": 0.3, "moderate": 0.15, "weak": 0.05}
            },
            "standard": {
                "primary": 6,       # 30 min - balanced approach
                "confirmation": 12, # 60 min - trend confirmation
                "reaction": 3,      # 15 min - entry timing
                "thresholds": {"strong": 0.5, "moderate": 0.2, "weak": 0.08}
            },
            "range_trading": {
                "primary": 12,      # 60 min - identify ranges
                "confirmation": 24, # 120 min - confirm range bounds
                "reaction": 4,      # 20 min - range entry timing
                "thresholds": {"strong": 0.4, "moderate": 0.2, "weak": 0.08}
            },
            "breakout": {
                "primary": 4,       # 20 min - breakout detection
                "confirmation": 8,  # 40 min - breakout confirmation
                "reaction": 2,      # 10 min - immediate entry
                "thresholds": {"strong": 0.6, "moderate": 0.3, "weak": 0.12}
            },
            "trend_following": {
                "primary": 18,      # 90 min - established trends
                "confirmation": 36, # 180 min - long-term confirmation
                "reaction": 6,      # 30 min - trend entry timing
                "thresholds": {"strong": 0.8, "moderate": 0.4, "weak": 0.15}
            },
            "spike_hunting": {
                "primary": 2,       # 10 min - ultra-fast spikes
                "confirmation": 4,  # 20 min - spike confirmation
                "reaction": 1,      # 5 min - immediate entry
                "thresholds": {"strong": 0.8, "moderate": 0.4, "weak": 0.15}
            },
            "low_volatility_range": {
                "primary": 15,      # 75 min - stable range detection
                "confirmation": 30, # 150 min - range confirmation
                "reaction": 5,      # 25 min - range entry timing
                "thresholds": {"strong": 0.3, "moderate": 0.15, "weak": 0.05}
            },
            "high_volatility": {
                "primary": 8,       # 40 min - volatility smoothing
                "confirmation": 16, # 80 min - volatility confirmation
                "reaction": 3,      # 15 min - volatility entry timing
                "thresholds": {"strong": 1.0, "moderate": 0.5, "weak": 0.2}
            }
        }
        
        return strategy_params.get(strategy_name, strategy_params["standard"])
    
    def calculate_multi_timeframe_trend(self, candles: List[Dict], strategy_name: str = "standard") -> Dict[str, Any]:
        """
        Calculate trend using strategy-specific multi-timeframe approach
        
        Args:
            candles: Historical candles (5m timeframe)
            strategy_name: Strategy name for period selection
            
        Returns:
            Dict with primary, confirmation, and reaction trends plus metadata
        """
        try:
            if len(candles) < 3:
                return {
                    "primary_trend": "SIDEWAYS",
                    "confirmation_trend": "SIDEWAYS", 
                    "reaction_trend": "SIDEWAYS",
                    "trend_consensus": "SIDEWAYS",
                    "strategy": strategy_name,
                    "periods_used": {"primary": 0, "confirmation": 0, "reaction": 0},
                    "error": "Insufficient data"
                }
            
            # Get strategy-specific periods
            params = self._get_strategy_trend_params(strategy_name)
            primary_period = params.get("primary", 6)
            confirmation_period = params.get("confirmation", 12) 
            reaction_period = params.get("reaction", 3)
            thresholds = params.get("thresholds", {"strong": 0.5, "moderate": 0.2, "weak": 0.08})
            
            # Calculate trends for each timeframe
            primary_trend = self._calculate_trend_for_period(candles, primary_period, thresholds, "primary")
            confirmation_trend = self._calculate_trend_for_period(candles, confirmation_period, thresholds, "confirmation")
            reaction_trend = self._calculate_trend_for_period(candles, reaction_period, thresholds, "reaction")
            
            # Determine consensus trend
            trend_consensus = self._determine_trend_consensus(primary_trend, confirmation_trend, reaction_trend)
            
            return {
                "primary_trend": primary_trend["trend"],
                "primary_strength": primary_trend["strength"],
                "primary_change_pct": primary_trend["change_pct"],
                
                "confirmation_trend": confirmation_trend["trend"],
                "confirmation_strength": confirmation_trend["strength"],
                "confirmation_change_pct": confirmation_trend["change_pct"],
                
                "reaction_trend": reaction_trend["trend"],
                "reaction_strength": reaction_trend["strength"],
                "reaction_change_pct": reaction_trend["change_pct"],
                
                "trend_consensus": trend_consensus,
                "strategy": strategy_name,
                "periods_used": {
                    "primary": f"{primary_period} candles ({primary_period * 5}min)",
                    "confirmation": f"{confirmation_period} candles ({confirmation_period * 5}min)",
                    "reaction": f"{reaction_period} candles ({reaction_period * 5}min)"
                },
                "timeframe": "5m",
                "data_source": f"multi_timeframe_{strategy_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe trend calculation failed: {e}")
            return {
                "primary_trend": "SIDEWAYS",
                "confirmation_trend": "SIDEWAYS",
                "reaction_trend": "SIDEWAYS", 
                "trend_consensus": "ERROR",
                "strategy": strategy_name,
                "error": str(e)
            }
    
    def _calculate_trend_for_period(self, candles: List[Dict], period: int, 
                                  thresholds: Dict[str, float], timeframe_name: str) -> Dict[str, Any]:
        """Calculate trend for a specific period"""
        try:
            # Use the most recent candles for the period
            period_candles = candles[-period:] if len(candles) >= period else candles
            
            if len(period_candles) < 2:
                return {"trend": "SIDEWAYS", "strength": 0.0, "change_pct": 0.0}
            
            # Calculate price change
            start_price = period_candles[0]["close"]
            end_price = period_candles[-1]["close"]
            change_pct = ((end_price - start_price) / start_price) * 100
            
            # Classify trend
            trend = self._classify_trend(change_pct, thresholds)
            
            # Calculate strength (consistency of direction)
            up_moves = sum(1 for i in range(1, len(period_candles)) 
                          if period_candles[i]["close"] > period_candles[i-1]["close"])
            total_moves = len(period_candles) - 1
            strength = up_moves / total_moves if total_moves > 0 else 0.0
            
            # Adjust strength for downtrend
            if change_pct < 0:
                strength = 1.0 - strength
            
            return {
                "trend": trend,
                "strength": round(strength, 3),
                "change_pct": round(change_pct, 3),
                "period_candles": len(period_candles),
                "timeframe_name": timeframe_name
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation for {timeframe_name} failed: {e}")
            return {"trend": "SIDEWAYS", "strength": 0.0, "change_pct": 0.0}
    
    def _determine_trend_consensus(self, primary: Dict, confirmation: Dict, reaction: Dict) -> str:
        """Determine overall trend consensus from multiple timeframes"""
        try:
            trends = [primary["trend"], confirmation["trend"], reaction["trend"]]
            
            # Count trend directions
            up_count = trends.count("UP") + trends.count("STRONG_UP")
            down_count = trends.count("DOWN") + trends.count("STRONG_DOWN")
            sideways_count = trends.count("SIDEWAYS")
            
            # Determine consensus
            if up_count >= 2:
                return "BULLISH_CONSENSUS"
            elif down_count >= 2:
                return "BEARISH_CONSENSUS"
            elif sideways_count >= 2:
                return "SIDEWAYS_CONSENSUS"
            else:
                return "MIXED_SIGNALS"
                
        except Exception as e:
            logger.error(f"❌ Trend consensus calculation failed: {e}")
            return "ERROR"


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
