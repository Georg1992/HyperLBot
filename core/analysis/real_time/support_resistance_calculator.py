#!/usr/bin/env python3
"""
Support/Resistance Calculator Module
Centralized support and resistance level calculations
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class SupportResistanceCalculator:
    """Centralized support and resistance calculation system"""
    
    def __init__(self):
        logger.info("📊 Support/Resistance Calculator initialized")
    
    def calculate_support_resistance(self, candles: List[Dict], lookback: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels from candle data"""
        try:
            if len(candles) < lookback:
                return {"support": 0.0, "resistance": 0.0}
            
            recent_candles = candles[-lookback:]
            highs = [float(candle.get("high", candle.get("close", 0))) for candle in recent_candles]
            lows = [float(candle.get("low", candle.get("close", 0))) for candle in recent_candles]
            
            # Calculate basic support and resistance
            resistance = max(highs) if highs else 0.0
            support = min(lows) if lows else 0.0
            
            return {
                "support": round(support, 2),
                "resistance": round(resistance, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Support/resistance calculation failed: {e}")
            return {"support": 0.0, "resistance": 0.0}
    
    def calculate_pivot_levels(self, candles: List[Dict], periods: int = 10) -> Dict[str, float]:
        """Calculate pivot point levels for advanced support/resistance"""
        try:
            if len(candles) < periods:
                return {"pivot": 0.0, "support1": 0.0, "resistance1": 0.0}
            
            recent_candles = candles[-periods:]
            
            # Calculate pivot point (average of high, low, close)
            highs = [float(candle.get("high", candle.get("close", 0))) for candle in recent_candles]
            lows = [float(candle.get("low", candle.get("close", 0))) for candle in recent_candles]
            closes = [float(candle.get("close", 0)) for candle in recent_candles]
            
            avg_high = sum(highs) / len(highs) if highs else 0.0
            avg_low = sum(lows) / len(lows) if lows else 0.0
            avg_close = sum(closes) / len(closes) if closes else 0.0
            
            pivot = (avg_high + avg_low + avg_close) / 3
            
            # Calculate support and resistance levels
            support1 = 2 * pivot - avg_high
            resistance1 = 2 * pivot - avg_low
            
            return {
                "pivot": round(pivot, 2),
                "support1": round(support1, 2),
                "resistance1": round(resistance1, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Pivot level calculation failed: {e}")
            return {"pivot": 0.0, "support1": 0.0, "resistance1": 0.0}
    
    def identify_key_levels(self, candles: List[Dict], min_touches: int = 2) -> Dict[str, Any]:
        """Identify key support/resistance levels based on price action"""
        try:
            if len(candles) < 10:
                return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
            
            # Extract price levels
            closes = [float(candle.get("close", 0)) for candle in candles]
            highs = [float(candle.get("high", candle.get("close", 0))) for candle in candles]
            lows = [float(candle.get("low", candle.get("close", 0))) for candle in candles]
            
            # Find potential support/resistance levels (simplified approach)
            price_range = max(closes) - min(closes)
            level_tolerance = price_range * 0.005  # 0.5% tolerance
            
            # Identify levels where price has bounced multiple times
            key_levels = []
            
            # Check for support levels (bounces from lows)
            unique_lows = list(set([round(low, -1) for low in lows]))  # Round to nearest $10
            for level in unique_lows:
                touches = sum(1 for low in lows if abs(low - level) <= level_tolerance)
                if touches >= min_touches:
                    key_levels.append({"level": level, "type": "support", "touches": touches})
            
            # Check for resistance levels (rejections from highs)
            unique_highs = list(set([round(high, -1) for high in highs]))  # Round to nearest $10
            for level in unique_highs:
                touches = sum(1 for high in highs if abs(high - level) <= level_tolerance)
                if touches >= min_touches:
                    key_levels.append({"level": level, "type": "resistance", "touches": touches})
            
            # Find strongest levels
            support_levels = [lvl for lvl in key_levels if lvl["type"] == "support"]
            resistance_levels = [lvl for lvl in key_levels if lvl["type"] == "resistance"]
            
            strongest_support = max(support_levels, key=lambda x: x["touches"])["level"] if support_levels else min(lows)
            strongest_resistance = max(resistance_levels, key=lambda x: x["touches"])["level"] if resistance_levels else max(highs)
            
            return {
                "key_levels": key_levels,
                "strongest_support": round(strongest_support, 2),
                "strongest_resistance": round(strongest_resistance, 2),
                "level_count": len(key_levels)
            }
            
        except Exception as e:
            logger.error(f"❌ Key level identification failed: {e}")
            return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}