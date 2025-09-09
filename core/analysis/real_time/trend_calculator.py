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
            if len(candles) < 8:  # Updated to match new candle count
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0, "confidence": 0}
            
            # Get recent closes (ENHANCED: Use more candles for better trend detection)
            recent_closes = [candle["close"] for candle in candles[-8:]]  # Increased from 5 to 8 candles
            
            # Calculate basic trend metrics (ORIGINAL LOGIC)
            first_price = recent_closes[0]
            last_price = recent_closes[-1]
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            # ENHANCED: Check for recent significant moves (last 3 candles)
            if len(recent_closes) >= 3:
                recent_3_closes = recent_closes[-3:]
                recent_first = recent_3_closes[0]
                recent_last = recent_3_closes[-1]
                recent_change_pct = abs((recent_last - recent_first) / recent_first) * 100
                
                # If recent 3-candle move is significant (>0.3%), boost the overall trend
                if recent_change_pct > 0.3:
                    # Boost the price change percentage to reflect recent momentum
                    price_change_pct = price_change_pct * 1.5  # 50% boost for recent significant moves
                    logger.debug(f"📈 Recent significant move detected: {recent_change_pct:.2f}% - boosting trend calculation")
            
            # Calculate trend consistency with improved logic
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
                # No move (equal prices) doesn't count toward total
            
            if total_moves == 0:
                strength = 0
            else:
                # Calculate strength as consistency of direction
                dominant_moves = max(up_moves, down_moves)
                strength = dominant_moves / total_moves
                
                # Boost strength if there's a clear directional bias
                if dominant_moves >= 3:  # At least 3 moves in same direction
                    strength = min(1.0, strength * 1.2)  # Boost by 20%
            
            # Calculate momentum (ORIGINAL LOGIC)
            momentum = self._calculate_momentum(recent_closes)
            
            # Calculate volume confirmation (ORIGINAL LOGIC)
            volume_confirmation = self._check_volume_confirmation(candles[-5:])
            
            # Calculate trend acceleration (rate of change in momentum)
            acceleration = self._calculate_acceleration(recent_closes)
            
            # Determine trend with IMPROVED THRESHOLDS for Bitcoin 5m trading
            # Balance: Price movement is primary, but strength/momentum still matter
            if abs(price_change_pct) > 0.20 and strength > 0.5:
                # Very strong trends - more realistic thresholds
                if price_change_pct > 0.20 and momentum > 0.0005:
                    trend = "STRONG_UPTREND"
                    direction = 1
                elif price_change_pct < -0.20 and momentum < -0.0005:
                    trend = "STRONG_DOWNTREND"
                    direction = -1
                else:
                    trend = "SIDEWAYS"
                    direction = 0
            elif abs(price_change_pct) > 0.08 and strength > 0.3:
                # Strong trends - more realistic thresholds
                if price_change_pct > 0.08 and momentum > 0.0002:
                    trend = "UPTREND"
                    direction = 1
                elif price_change_pct < -0.08 and momentum < -0.0002:
                    trend = "DOWNTREND"
                    direction = -1
                else:
                    trend = "SIDEWAYS"
                    direction = 0
            elif abs(price_change_pct) > 0.02 and strength > 0.15:
                # Weak trends - more sensitive to catch clear moves (reduced thresholds)
                if price_change_pct > 0.02 and momentum > 0.00005:
                    trend = "WEAK_UPTREND"
                    direction = 1
                elif price_change_pct < -0.02 and momentum < -0.00005:
                    trend = "WEAK_DOWNTREND"
                    direction = -1
                else:
                    trend = "SIDEWAYS"
                    direction = 0
            elif abs(price_change_pct) > 0.015:  # Fallback: prioritize price movement for very weak trends
                # Very weak trends - price movement alone can indicate direction
                if price_change_pct > 0.015:
                    trend = "WEAK_UPTREND"
                    direction = 1
                elif price_change_pct < -0.015:
                    trend = "WEAK_DOWNTREND"
                    direction = -1
            else:
                # No clear trend - sideways movement
                trend = "SIDEWAYS"
                direction = 0
            
            return {
                "trend": trend,
                "strength": round(strength, 3),
                "direction": direction,
                "momentum": round(momentum, 6),
                "acceleration": round(acceleration, 8),
                "price_change": round(price_change_pct, 3),
                "volume_confirmation": volume_confirmation,
                "timeframe": timeframe,
                "data_source": "improved_trend_logic"
            }
            
        except Exception as e:
            logger.error(f"❌ Trend calculation failed: {e}")
            return self._get_default_trend()
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum with improved stability"""
        if len(prices) < 2:
            return 0.0
        
        # Calculate momentum as weighted average rate of change
        if len(prices) >= 4:
            # Use 4-period weighted momentum for better stability
            # More weight to recent periods
            momentum_1 = (prices[-1] - prices[-2]) / prices[-2]  # Most recent
            momentum_2 = (prices[-2] - prices[-3]) / prices[-3]  # Second most recent
            momentum_3 = (prices[-3] - prices[-4]) / prices[-4]  # Third most recent
            
            # Weighted average: 50% recent, 30% second, 20% third
            momentum = (momentum_1 * 0.5) + (momentum_2 * 0.3) + (momentum_3 * 0.2)
        elif len(prices) >= 3:
            # Use 3-period momentum for better stability
            momentum_1 = (prices[-1] - prices[-2]) / prices[-2]
            momentum_2 = (prices[-2] - prices[-3]) / prices[-3]
            momentum = (momentum_1 * 0.6) + (momentum_2 * 0.4)  # Weighted average
        else:
            # Single period momentum
            momentum = (prices[-1] - prices[-2]) / prices[-2]
        
        return momentum
    
    def _calculate_acceleration(self, prices: List[float]) -> float:
        """Calculate trend acceleration (rate of change in momentum)"""
        if len(prices) < 4:
            return 0.0
        
        # Calculate momentum for recent periods
        momentum_recent = self._calculate_momentum(prices[-3:])  # Last 3 periods
        momentum_previous = self._calculate_momentum(prices[-4:-1])  # Previous 3 periods
        
        # Acceleration is the change in momentum
        acceleration = momentum_recent - momentum_previous
        
        return acceleration
    
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
        """Get default trend data when calculation fails"""
        return {
            "trend": "SIDEWAYS",
            "strength": 0,
            "direction": 0,
            "confidence": 0,
            "momentum": 0.0,
            "acceleration": 0.0,
            "volume_confirmation": False,
            "timeframe": "unknown",
            "data_source": "default_fallback"
        }