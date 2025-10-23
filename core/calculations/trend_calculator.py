#!/usr/bin/env python3
"""
Trend Calculator Module
Simple, working trend calculation
"""

import time
from typing import Dict, Any, List
from loguru import logger


class TrendCalculator:
    """Simple trend calculation system"""
    
    def __init__(self):
        logger.info("📈 Trend Calculator initialized - Simple working logic")
    
    def get_latest_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get latest trend analysis for MarketDataService coordination"""
        try:
            # Get candles from HistoricalDataService
            from core.services.historical_data_service import get_global_historical_data_service
            historical_service = get_global_historical_data_service()
            
            # Get candles for all timeframes
            candles_5m = historical_service.get_5m_candles("BTC", 30)
            candles_1h = historical_service.get_1h_candles("BTC", 30)
            candles_1d = historical_service.get_1d_candles("BTC", 30)
            
            if not candles_5m or len(candles_5m) < 3:
                return {
                    "trend_15m": "SIDEWAYS",
                    "trend_1h": "SIDEWAYS", 
                    "trend_4h": "SIDEWAYS",
                    "trend_24h": "SIDEWAYS",
                    "timestamp": time.time(),
                    "data_type": "trend",
                    "error": "Insufficient candle data"
                }
            
            # Calculate universal multi-timeframe trends
            trend_analysis = self.calculate_universal_trends(candles_5m, candles_1h, candles_1d)
            
            return {
                "trend_15m": trend_analysis.get("trend_15m", "SIDEWAYS"),
                "trend_1h": trend_analysis.get("trend_1h", "SIDEWAYS"),
                "trend_4h": trend_analysis.get("trend_4h", "SIDEWAYS"),
                "trend_24h": trend_analysis.get("trend_24h", "SIDEWAYS"),
                "timestamp": time.time(),
                "data_type": "trend",
                "full_analysis": trend_analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest trend analysis: {e}")
            return {
                "trend_15m": "SIDEWAYS",
                "trend_1h": "SIDEWAYS",
                "trend_4h": "SIDEWAYS", 
                "trend_24h": "SIDEWAYS",
                "timestamp": time.time(),
                "data_type": "trend",
                "error": str(e)
            }
    
    def calculate_universal_trends(self, candles_5m: List[Dict], candles_1h: List[Dict], candles_1d: List[Dict]) -> Dict[str, Any]:
        """
        Calculate universal multi-timeframe trends (15m, 1h, 4h, 24h)
        
        Args:
            candles_5m: 5-minute candles for 15m trend
            candles_1h: 1-hour candles for 1h and 4h trends  
            candles_1d: 1-day candles for 24h trend
            
        Returns:
            Dict with trend_15m, trend_1h, trend_4h, trend_24h
        """
        try:
            # Universal thresholds for all timeframes
            thresholds = {"strong": 0.5, "moderate": 0.2, "weak": 0.08}
            
            # Calculate 15m trend (3 candles from 5m data)
            trend_15m = self._calculate_trend_for_period(candles_5m, 3, thresholds, "15m")
            
            # Calculate 1h trend (1 candle from 1h data)
            trend_1h = self._calculate_trend_for_period(candles_1h, 1, thresholds, "1h")
            
            # Calculate 4h trend (4 candles from 1h data)
            trend_4h = self._calculate_trend_for_period(candles_1h, 4, thresholds, "4h")
            
            # Calculate 24h trend (1 candle from 1d data)
            trend_24h = self._calculate_trend_for_period(candles_1d, 1, thresholds, "24h")
            
            return {
                "trend_15m": trend_15m["trend"],
                "trend_1h": trend_1h["trend"],
                "trend_4h": trend_4h["trend"],
                "trend_24h": trend_24h["trend"],
                "details": {
                    "15m": trend_15m,
                    "1h": trend_1h,
                    "4h": trend_4h,
                    "24h": trend_24h
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Universal trends calculation failed: {e}")
            return {
                "trend_15m": "SIDEWAYS",
                "trend_1h": "SIDEWAYS",
                "trend_4h": "SIDEWAYS",
                "trend_24h": "SIDEWAYS",
                "error": str(e)
            }
    
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
