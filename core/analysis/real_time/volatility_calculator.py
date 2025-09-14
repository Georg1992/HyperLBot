#!/usr/bin/env python3
"""
Volatility Calculator Module
Centralized volatility calculations from different data sources
"""

from typing import Dict, Any, List, Optional
from loguru import logger


class VolatilityCalculator:
    """Centralized volatility calculation system"""
    
    def __init__(self):
        logger.info("📊 Volatility Calculator initialized")
    
    def calculate_candle_volatility(self, candles: List[Dict], timeframe: str = "5m") -> float:
        """Calculate volatility from candle data using HIGHLY REACTIVE method for real-time trading"""
        try:
            if len(candles) < 3:  # Reduced minimum requirement for faster response
                return self._get_default_volatility(timeframe)
            
            # Use only the most recent 6 candles for maximum reactivity (30 minutes of 5m data)
            recent_candles = candles[-6:] if len(candles) >= 6 else candles
            
            # Method 1: Weighted recent candle volatilities (most reactive to current market)
            weighted_volatilities = []
            total_weight = 0
            
            for i, candle in enumerate(recent_candles):
                if candle["close"] > 0 and candle["high"] > 0 and candle["low"] > 0:
                    range_vol = (candle["high"] - candle["low"]) / candle["close"]
                    # Give exponentially more weight to recent candles
                    weight = (i + 1) ** 2  # 1, 4, 9, 16, 25, 36 for 6 candles
                    weighted_volatilities.append(range_vol * weight)
                    total_weight += weight
            
            if weighted_volatilities and total_weight > 0:
                # Calculate weighted average (most recent candles have much higher impact)
                weighted_avg_volatility = sum(weighted_volatilities) / total_weight
                
                # Method 2: Recent price momentum (captures directional movement)
                if len(recent_candles) >= 3:
                    recent_momentum = 0
                    for i in range(1, len(recent_candles)):
                        if recent_candles[i-1]["close"] > 0:
                            momentum = abs(recent_candles[i]["close"] - recent_candles[i-1]["close"]) / recent_candles[i-1]["close"]
                            # Give more weight to recent momentum
                            weight = (len(recent_candles) - i) ** 1.5
                            recent_momentum += momentum * weight
                    
                    # Average momentum with weight
                    momentum_weight = sum((len(recent_candles) - i) ** 1.5 for i in range(1, len(recent_candles)))
                    if momentum_weight > 0:
                        recent_momentum = recent_momentum / momentum_weight
                        
                        # Combine weighted volatility with recent momentum (70% volatility, 30% momentum)
                        combined_volatility = (weighted_avg_volatility * 0.7) + (recent_momentum * 0.3)
                        return round(combined_volatility, 6)
                
                return round(weighted_avg_volatility, 6)
            
            # Fallback: Calculate returns from close prices (original method)
            returns = []
            for i in range(1, len(candles)):
                if candles[i-1]["close"] > 0:
                    ret = (candles[i]["close"] - candles[i-1]["close"]) / candles[i-1]["close"]
                    returns.append(abs(ret))
            
            if not returns:
                return self._get_default_volatility(timeframe)
            
            # Use median for returns too (robust against outliers)
            returns.sort()
            n = len(returns)
            if n % 2 == 0:
                median_returns = (returns[n//2 - 1] + returns[n//2]) / 2
            else:
                median_returns = returns[n//2]
            
            return round(median_returns, 6)
            
        except Exception as e:
            logger.warning(f"Candle volatility calculation failed: {e}")
            return self._get_default_volatility(timeframe)
    
    # Redundant wrapper methods removed - call calculate_candle_volatility() directly
    # Eliminated: calculate_volatility_5m, calculate_volatility_1h, calculate_volatility_1d
    
    # calculate_orderbook_volatility() removed - redundant wrapper for OrderbookAnalyzer.get_volatility_analysis()
    # Use OrderbookAnalyzer.get_volatility_analysis() directly instead
    
    def categorize_5m_volatility_for_trading(self, volatility_5m: float) -> tuple:
        """Categorize 5m volatility for trading decisions using centralized constants"""
        try:
            # Import centralized constants for consistency
            from core.constants import VariabilityConstants
            
            # Use centralized 5-minute volatility thresholds (corrected range logic)
            if volatility_5m >= VariabilityConstants.VOLATILITY_5M_EXTREME:  # >= 0.6% (extreme 5m movement)
                category = "EXTREME"
                trend = "VOLATILE"
            elif volatility_5m >= VariabilityConstants.VOLATILITY_5M_HIGH:    # >= 0.3% (high 5m activity)
                category = "HIGH"
                trend = "ACTIVE"
            elif volatility_5m >= VariabilityConstants.VOLATILITY_5M_MODERATE:  # >= 0.15% (moderate 5m movement)
                category = "MODERATE" 
                trend = "NORMAL"
            elif volatility_5m >= VariabilityConstants.VOLATILITY_5M_LOW:     # >= 0.08% (low but noticeable 5m movement)
                category = "LOW"
                trend = "QUIET"
            elif volatility_5m >= VariabilityConstants.VOLATILITY_5M_VERY_LOW: # >= 0.03% (very low 5m movement)
                category = "LOW"  # FIXED: This should be LOW, not VERY_LOW
                trend = "QUIET"
            else:                                                              # < 0.03% (extremely low 5m movement)
                category = "VERY_LOW"
                trend = "BORING"
            
            return category, trend
            
        except Exception as e:
            logger.error(f"❌ 5m volatility categorization failed: {e}")
            return "ERROR", "ERROR"
    
    # calculate_momentum_volatility() removed - dead code (never called)
    # Complex 42-line momentum calculation that was never used
    
    def _get_default_volatility(self, timeframe: str) -> float:
        """Get default volatility values for different timeframes - REALISTIC Bitcoin ranges"""
        defaults = {
            "1m": 0.0005,    # 0.05% - very quiet Bitcoin 1-min
            "5m": 0.001,     # 0.1% - quiet Bitcoin 5-min  
            "1h": 0.002,     # 0.2% - normal Bitcoin 1-hour
            "1d": 0.005      # 0.5% - normal Bitcoin daily
        }
        return defaults.get(timeframe, 0.001)
    
    # _get_default_orderbook_volatility() removed - was only used by eliminated calculate_orderbook_volatility()
