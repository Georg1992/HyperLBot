#!/usr/bin/env python3
"""
Yahoo Finance Momentum Analyzer
Handles momentum analysis, RSI calculations, and trend detection
"""

# import time  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger
# # from datetime import datetime, timedelta  # Removed unused import  # Removed unused import
# from core.constants import technical_constants, data_constants  # Removed unused import

class YahooMomentumAnalyzer:
    """Momentum analysis and RSI calculations for Yahoo Finance data"""
    
    def __init__(self):
        logger.info("📈 Yahoo Momentum Analyzer initialized")
    
    def analyze_momentum(self, candles: List[Dict], symbol: str = "BTC") -> Dict[str, Any]:
        """Analyze momentum from candle data"""
        try:
            if not candles or len(candles) < 5:
                return {
                    "momentum": "UNKNOWN",
                    "direction": 0,
                    "strength": 0.0,
                    "acceleration": 0.0,
                    "error": "insufficient_data",
                    "data_source": "yahoo_finance"
                }
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(candles)):
                prev_close = candles[i-1]["close"]
                curr_close = candles[i]["close"]
                if prev_close > 0:
                    change = (curr_close - prev_close) / prev_close
                    price_changes.append(change)
            
            if not price_changes:
                return {
                    "momentum": "UNKNOWN",
                    "direction": 0,
                    "strength": 0.0,
                    "acceleration": 0.0,
                    "error": "no_price_changes",
                    "data_source": "yahoo_finance"
                }
            
            # Calculate momentum indicators
            recent_changes = price_changes[-3:]  # Last 3 changes
            price_change_1 = recent_changes[-1] if recent_changes else 0
            price_change_2 = recent_changes[-2] if len(recent_changes) > 1 else 0
            
            # Calculate momentum acceleration
            momentum_acceleration = price_change_1 - price_change_2
            
            # Determine momentum direction and strength
            if price_change_1 > technical_constants.PRICE_CHANGE_SIGNIFICANT and momentum_acceleration > 0:
                momentum = "STRONG_UP"
                direction = 1
                strength = min(abs(price_change_1) * 50, 0.5)
            elif price_change_1 < -technical_constants.PRICE_CHANGE_SIGNIFICANT and momentum_acceleration < 0:
                momentum = "STRONG_DOWN"
                direction = -1
                strength = min(abs(price_change_1) * 50, 0.5)
            elif price_change_1 > technical_constants.PRICE_CHANGE_MINOR:
                momentum = "WEAK_UP"
                direction = 1
                strength = min(abs(price_change_1) * 30, 0.3)
            elif price_change_1 < -technical_constants.PRICE_CHANGE_MINOR:
                momentum = "WEAK_DOWN"
                direction = -1
                strength = min(abs(price_change_1) * 30, 0.3)
            else:
                momentum = "SIDEWAYS"
                direction = 0
                strength = 0.0
            
            return {
                "momentum": momentum,
                "direction": direction,
                "strength": strength,
                "acceleration": momentum_acceleration,
                "price_change_1": price_change_1,
                "price_change_2": price_change_2,
                "recent_changes": recent_changes,
                "data_source": "yahoo_finance"
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze momentum: {e}")
            return {
                "momentum": "ERROR",
                "direction": 0,
                "strength": 0.0,
                "acceleration": 0.0,
                "error": str(e),
                "data_source": "yahoo_finance"
            }
    

# Global instance
momentum_analyzer = YahooMomentumAnalyzer()
