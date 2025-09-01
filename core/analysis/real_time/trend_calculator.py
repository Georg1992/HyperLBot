#!/usr/bin/env python3
"""
Trend Calculator Module
Centralized trend calculations using ORIGINAL WORKING LOGIC from trend_manager
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class TrendCalculator:
    """Centralized trend calculation system using original working trend logic"""
    
    def __init__(self):
        logger.info("📈 Trend Calculator initialized - Using original working logic")
    
    def calculate_trend(self, candles: List[Dict], timeframe: str = "5m") -> Dict[str, Any]:
        """Calculate trend using ORIGINAL WORKING LOGIC (moved from trend_manager)"""
        try:
            if len(candles) < 5:
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
            
            # Get recent closes (ORIGINAL LOGIC)
            recent_closes = [candle["close"] for candle in candles[-5:]]
            
            # Calculate basic trend metrics (ORIGINAL LOGIC)
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            # Calculate trend consistency (ORIGINAL LOGIC)
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
            
            # Calculate momentum (ORIGINAL LOGIC)
            momentum = self._calculate_momentum(recent_closes)
            
            # Calculate volume confirmation (ORIGINAL LOGIC)
            volume_confirmation = self._check_volume_confirmation(candles[-5:])
            
            # Determine trend with SENSITIVE THRESHOLDS for all original states
            if abs(price_change_pct) > 0.3 and strength > 0.7:
                # Strong trends first
                if price_change_pct > 0.3 and momentum > 0:
                    trend = "STRONG_UPTREND"
                    direction = 1
                elif price_change_pct < -0.3 and momentum < 0:
                    trend = "STRONG_DOWNTREND"
                    direction = -1
                else:
                    trend = "SIDEWAYS"
                    direction = 0
            elif price_change_pct > 0.05 and strength > 0.3 and momentum > 0:
                trend = "UPTREND"
                direction = 1
            elif price_change_pct < -0.05 and strength > 0.3 and momentum < 0:
                trend = "DOWNTREND"
                direction = -1
            elif price_change_pct > 0.01 and momentum > 0:
                # Weak uptrend - very sensitive
                trend = "WEAK_UPTREND"
                direction = 1
            elif price_change_pct < -0.01 and momentum < 0:
                # Weak downtrend - very sensitive
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
                "price_change": round(price_change_pct, 3),
                "volume_confirmation": volume_confirmation,
                "timeframe": timeframe,
                "data_source": "original_working_logic"
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return self._get_default_trend()
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum (ORIGINAL WORKING LOGIC from trend_manager)"""
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
        """Check if volume confirms the trend (ORIGINAL WORKING LOGIC)"""
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
    
    def _get_default_trend(self) -> Dict[str, Any]:
        """Get default trend data when calculation fails (ORIGINAL STRUCTURE)"""
        return {
            "trend": "SIDEWAYS",
            "strength": 0,
            "direction": 0,
            "confidence": 0,
            "momentum": 0.0,
            "volume_confirmation": False,
            "timeframe": "unknown",
            "data_source": "default_fallback"
        }