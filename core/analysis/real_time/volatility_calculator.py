#!/usr/bin/env python3
"""
Volatility Calculator Module
Centralized volatility calculations from different data sources
"""

import statistics
from typing import Dict, Any, List, Optional
from loguru import logger


class VolatilityCalculator:
    """Centralized volatility calculation system"""
    
    def __init__(self):
        logger.info("📊 Volatility Calculator initialized")
    
    def calculate_candle_volatility(self, candles: List[Dict], timeframe: str = "5m") -> float:
        """Calculate volatility from candle data using comprehensive method (captures overall market movement)"""
        try:
            if len(candles) < 10:
                return self._get_default_volatility(timeframe)
            
            # Method 1: Overall price movement volatility (captures multi-candle trends)
            if len(candles) >= 5:
                # Calculate overall movement from first to last candle
                first_candle = candles[0]
                last_candle = candles[-1]
                
                if first_candle["close"] > 0 and last_candle["close"] > 0:
                    overall_movement = abs(last_candle["close"] - first_candle["close"]) / first_candle["close"]
                    
                    # Also calculate the maximum range across all candles
                    max_high = max(candle["high"] for candle in candles if candle["high"] > 0)
                    min_low = min(candle["low"] for candle in candles if candle["low"] > 0)
                    max_range = (max_high - min_low) / first_candle["close"]
                    
                    # Use the higher of overall movement or max range (captures both trends and spikes)
                    overall_volatility = max(overall_movement, max_range)
                    
                    # For 5-minute timeframe, use the overall volatility directly (don't scale down)
                    # This captures the actual market movement across the timeframe
                    if overall_volatility > 0:
                        return round(overall_volatility, 6)
            
            # Method 2: Range-based volatility (high-low)/close - fallback for individual candles
            range_volatilities = []
            for candle in candles:
                if candle["close"] > 0 and candle["high"] > 0 and candle["low"] > 0:
                    range_vol = (candle["high"] - candle["low"]) / candle["close"]
                    range_volatilities.append(range_vol)
            
            if range_volatilities:
                # Use average range volatility (more representative of actual price action)
                volatility = sum(range_volatilities) / len(range_volatilities)
                return round(volatility, 6)
            
            # Fallback: Calculate returns from close prices (original method)
            returns = []
            for i in range(1, len(candles)):
                if candles[i-1]["close"] > 0:
                    ret = (candles[i]["close"] - candles[i-1]["close"]) / candles[i-1]["close"]
                    returns.append(abs(ret))
            
            if not returns:
                return self._get_default_volatility(timeframe)
            
            # Calculate average volatility
            volatility = sum(returns) / len(returns)
            return round(volatility, 6)
            
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
