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
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            
            # Get candles for all timeframes (with error handling for each)
            candles_5m = []
            candles_1h = []
            candles_1d = []
            
            try:
                candles_5m = historical_service.get_5m_candles("BTC", 30)
            except Exception as e:
                logger.warning(f"⚠️ Failed to get 5m candles: {e}")
                candles_5m = []
            
            try:
                candles_1h = historical_service.get_1h_candles("BTC", 30)
            except ValueError as e:
                # ValueError means insufficient 5m candles in database for aggregation
                logger.warning(f"⚠️ Failed to get 1h candles (need 360 5m candles): {e}")
                candles_1h = []
            except Exception as e:
                logger.warning(f"⚠️ Failed to get 1h candles: {e}")
                candles_1h = []
            
            try:
                candles_1d = historical_service.get_1d_candles("BTC", 30)
            except ValueError as e:
                # ValueError means insufficient 5m candles in database for aggregation
                logger.warning(f"⚠️ Failed to get 1d candles (need 8,640 5m candles): {e}")
                candles_1d = []
            except Exception as e:
                logger.warning(f"⚠️ Failed to get 1d candles: {e}")
                candles_1d = []
            
            # Check if we have sufficient data
            if len(candles_5m) < 3:
                logger.warning(f"⚠️ Insufficient 5m candles: {len(candles_5m)} (need at least 3)")
                return {
                    "trend_15m": "UNKNOWN",
                    "trend_1h": "UNKNOWN", 
                    "trend_4h": "UNKNOWN",
                    "trend_24h": "UNKNOWN",
                    "timestamp": time.time(),
                    "data_type": "trend",
                    "error": f"Insufficient 5m candle data: {len(candles_5m)} < 3"
                }
            
            # Calculate universal multi-timeframe trends
            trend_analysis = self.calculate_universal_trends(candles_5m, candles_1h, candles_1d)
            
            return {
                "trend_15m": trend_analysis.get("trend_15m", "UNKNOWN"),
                "trend_1h": trend_analysis.get("trend_1h", "UNKNOWN"),
                "trend_4h": trend_analysis.get("trend_4h", "UNKNOWN"),
                "trend_24h": trend_analysis.get("trend_24h", "UNKNOWN"),
                "timestamp": time.time(),
                "data_type": "trend",
                "full_analysis": trend_analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest trend analysis: {e}")
            return {
                "trend_15m": "UNKNOWN",
                "trend_1h": "UNKNOWN",
                "trend_4h": "UNKNOWN", 
                "trend_24h": "UNKNOWN",
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
            # Timeframe-specific thresholds (adjusted for shorter timeframes)
            # 15m: Lower thresholds since it's a very short period
            thresholds_15m = {"strong": 0.3, "moderate": 0.15, "weak": 0.05}
            # 1h: Standard thresholds
            thresholds_1h = {"strong": 0.5, "moderate": 0.2, "weak": 0.08}
            # 4h: Slightly higher thresholds for longer period
            thresholds_4h = {"strong": 0.8, "moderate": 0.4, "weak": 0.15}
            # 24h: Higher thresholds for daily trends
            thresholds_24h = {"strong": 2.0, "moderate": 1.0, "weak": 0.3}
            
            # Calculate 15m trend (3 candles from 5m data) with adjusted thresholds
            if candles_5m and len(candles_5m) >= 3:
                trend_15m = self._calculate_trend_for_period(candles_5m, 3, thresholds_15m, "15m")
            else:
                trend_15m = {"trend": "UNKNOWN", "strength": 0.0, "change_pct": 0.0}
            
            # Calculate 1h trend (1 candle from 1h data)
            if candles_1h and len(candles_1h) >= 1:
                trend_1h = self._calculate_trend_for_period(candles_1h, 1, thresholds_1h, "1h")
            else:
                trend_1h = {"trend": "UNKNOWN", "strength": 0.0, "change_pct": 0.0}
            
            # Calculate 4h trend (4 candles from 1h data)
            if candles_1h and len(candles_1h) >= 4:
                trend_4h = self._calculate_trend_for_period(candles_1h, 4, thresholds_4h, "4h")
            else:
                trend_4h = {"trend": "UNKNOWN", "strength": 0.0, "change_pct": 0.0}
            
            # Calculate 24h trend (1 candle from 1d data)
            if candles_1d and len(candles_1d) >= 1:
                trend_24h = self._calculate_trend_for_period(candles_1d, 1, thresholds_24h, "24h")
            else:
                trend_24h = {"trend": "UNKNOWN", "strength": 0.0, "change_pct": 0.0}
            
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
                "trend_15m": "UNKNOWN",
                "trend_1h": "UNKNOWN",
                "trend_4h": "UNKNOWN",
                "trend_24h": "UNKNOWN",
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

# Factory function for dependency injection
def create_trend_calculator() -> TrendCalculator:
    """
    Factory function to create TrendCalculator with dependency injection
    
    Returns:
        Configured TrendCalculator instance
    """
    return TrendCalculator()

# Deprecated singleton functions removed - use create_trend_calculator() instead
