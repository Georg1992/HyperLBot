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
        """Calculate volatility from candle data (Yahoo Finance style)"""
        try:
            if len(candles) < 10:
                return self._get_default_volatility(timeframe)
            
            # Calculate returns from close prices
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
        """Categorize 5m volatility for trading decisions (adjusted for 5m trading reality)"""
        try:
            # Categorize based on 5-minute trading relevance (adjusted thresholds for realistic 5m trading)
            if volatility_5m > 0.010:      # > 1.0% (extreme 5m movement)
                category = "EXTREME"
                trend = "VOLATILE"
            elif volatility_5m > 0.005:    # > 0.5% (high 5m activity)
                category = "HIGH"
                trend = "ACTIVE"
            elif volatility_5m > 0.002:    # > 0.2% (moderate 5m movement - user's chart level)
                category = "MODERATE" 
                trend = "NORMAL"
            elif volatility_5m > 0.001:    # > 0.1% (low but noticeable 5m movement)
                category = "LOW"
                trend = "QUIET"
            else:                          # < 0.1% (very low 5m movement)
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
