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
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest trend analysis for MarketDataService coordination - NO FALLBACKS
        
        Strategy-independent: Returns objective trend analysis for all timeframes.
        No strategy-specific filtering or bias.
        """
        try:
            # Get candles from HistoricalDataService - NO FALLBACKS
            from core.services.historical_data_service import create_historical_data_service
            historical_service = create_historical_data_service()
            
            # Get candles for all timeframes - must succeed or raise
            from config.config import TradingConfig
            symbol = TradingConfig.SYMBOL
            candles_5m = historical_service.get_5m_candles(symbol, 30)
            candles_1h = historical_service.get_1h_candles(symbol, 30)
            candles_1d = historical_service.get_1d_candles(symbol, 30)
            
            # Validate minimum required data - NO FALLBACKS
            if not candles_5m or len(candles_5m) < 3:
                raise ValueError(f"Insufficient 5m candles for trend calculation: {len(candles_5m) if candles_5m else 0} < 3 - NO FALLBACKS")
            
            # Calculate universal multi-timeframe trends
            trend_analysis = self.calculate_universal_trends(candles_5m, candles_1h, candles_1d)
            
            return {
                "trend_15m": trend_analysis["trend_15m"],
                "trend_1h": trend_analysis["trend_1h"],
                "trend_4h": trend_analysis["trend_4h"],
                "trend_24h": trend_analysis["trend_24h"],
                "details": trend_analysis["details"],  # Include details for strength calculation (NO FALLBACKS)
                "timestamp": time.time(),
                "data_type": "trend"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest trend analysis: {e}")
            raise
    
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
            
            # Calculate 15m trend (3 candles from 5m data) with adjusted thresholds - NO FALLBACKS
            if not candles_5m or len(candles_5m) < 3:
                raise ValueError(f"Insufficient 5m candles for 15m trend: {len(candles_5m) if candles_5m else 0} < 3 - NO FALLBACKS")
            trend_15m = self._calculate_trend_for_period(candles_5m, 3, thresholds_15m, "15m")
            
            # Calculate 1h trend (1 candle from 1h data) - NO FALLBACKS
            if not candles_1h or len(candles_1h) < 1:
                raise ValueError(f"Insufficient 1h candles for 1h trend: {len(candles_1h) if candles_1h else 0} < 1 - NO FALLBACKS")
            trend_1h = self._calculate_trend_for_period(candles_1h, 1, thresholds_1h, "1h")
            
            # Calculate 4h trend (4 candles from 1h data) - NO FALLBACKS
            if not candles_1h or len(candles_1h) < 4:
                raise ValueError(f"Insufficient 1h candles for 4h trend: {len(candles_1h) if candles_1h else 0} < 4 - NO FALLBACKS")
            trend_4h = self._calculate_trend_for_period(candles_1h, 4, thresholds_4h, "4h")
            
            # Calculate 24h trend (1 candle from 1d data) - NO FALLBACKS
            if not candles_1d or len(candles_1d) < 1:
                raise ValueError(f"Insufficient 1d candles for 24h trend: {len(candles_1d) if candles_1d else 0} < 1 - NO FALLBACKS")
            trend_24h = self._calculate_trend_for_period(candles_1d, 1, thresholds_24h, "24h")
            
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
            raise
    
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
            raise
    


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
