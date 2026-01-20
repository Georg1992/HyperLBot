#!/usr/bin/env python3
"""
Pressure Analyzer Module
Handles complex pressure analysis and trend calculations
"""

import time
from typing import Dict, List, Any, Tuple
from loguru import logger
from core.constants import MagicNumbers


class PressureAnalyzer:
    """
    Analyzes market pressure using orderbook data.
    Handles complex pressure calculations and trend analysis.
    """
    
    def __init__(self):
        logger.debug("📊 PressureAnalyzer initialized")
    
    def categorize_pressure_direction(self, pressure_imbalance: float, depth_concentration: float) -> Tuple[str, float]:
        """
        Categorize pressure direction and strength.
        
        Args:
            pressure_imbalance: Pressure imbalance value
            depth_concentration: Depth concentration value
        
        Returns:
            Tuple of (direction, strength)
        """
        try:
            abs_imbalance = abs(pressure_imbalance)
            
            if pressure_imbalance > MagicNumbers.PRESSURE_STRONG_THRESHOLD:
                direction = "STRONG_BUY"
                strength = min(MagicNumbers.PRESSURE_MAX_STRENGTH, MagicNumbers.DEFAULT_STRENGTH + abs_imbalance)
            elif pressure_imbalance > MagicNumbers.PRESSURE_MODERATE_THRESHOLD:
                direction = "BUY"
                strength = MagicNumbers.DEFAULT_STRENGTH + (abs_imbalance * 2)
            elif pressure_imbalance < -MagicNumbers.PRESSURE_STRONG_THRESHOLD:
                direction = "STRONG_SELL"
                strength = min(MagicNumbers.PRESSURE_MAX_STRENGTH, MagicNumbers.DEFAULT_STRENGTH + abs_imbalance)
            elif pressure_imbalance < -MagicNumbers.PRESSURE_MODERATE_THRESHOLD:
                direction = "SELL"
                strength = MagicNumbers.DEFAULT_STRENGTH + (abs_imbalance * 2)
            else:
                direction = "NEUTRAL"
                strength = MagicNumbers.DEFAULT_STRENGTH - (abs_imbalance * 2)
            
            # Adjust strength based on depth concentration
            if depth_concentration > 0.8:
                strength *= 1.2  # Higher concentration = more reliable
            elif depth_concentration < 0.5:
                strength *= 0.8  # Lower concentration = less reliable
            
            return direction, max(0.0, min(1.0, strength))
            
        except Exception as e:
            logger.error(f"❌ Pressure direction categorization failed: {e}")
            return "NEUTRAL", 0.5
    
    def calculate_pressure_confidence(self, total_depth: float, pressure_imbalance: float) -> float:
        """
        Calculate confidence in pressure analysis.
        
        Args:
            total_depth: Total orderbook depth
            pressure_imbalance: Pressure imbalance value
        
        Returns:
            Confidence value (0-1)
        """
        try:
            # Base confidence on depth
            depth_confidence = min(1.0, total_depth / 100.0)  # Normalize depth
            
            # Adjust based on imbalance magnitude
            imbalance_confidence = min(1.0, abs(pressure_imbalance) * 2)
            
            # Combined confidence
            confidence = (depth_confidence * 0.7) + (imbalance_confidence * 0.3)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"❌ Pressure confidence calculation failed: {e}")
            return 0.5
    
    def determine_pressure_trend(self, pressure_imbalance: float, depth_concentration: float) -> str:
        """
        Determine pressure trend direction.
        
        Args:
            pressure_imbalance: Pressure imbalance value
            depth_concentration: Depth concentration value
        
        Returns:
            Trend direction string
        """
        try:
            # Determine trend based on imbalance and concentration
            if pressure_imbalance > 0.1 and depth_concentration > 0.7:
                return "BULLISH"
            elif pressure_imbalance < -0.1 and depth_concentration > 0.7:
                return "BEARISH"
            elif abs(pressure_imbalance) < 0.05:
                return "NEUTRAL"
            else:
                return "MIXED"
                
        except Exception as e:
            logger.error(f"❌ Pressure trend determination failed: {e}")
            return "UNKNOWN"
    
    def analyze_pressure_stability(self, pressure_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze pressure stability over time.
        
        Args:
            pressure_history: List of historical pressure data
        
        Returns:
            Dictionary with stability analysis
        """
        try:
            if len(pressure_history) < 3:
                return {
                    "stability": "UNKNOWN",
                    "volatility": 0.0,
                    "trend_consistency": 0.0
                }
            
            # Extract pressure imbalances
            imbalances = [p["pressure_imbalance"] if "pressure_imbalance" in p else 0.0 for p in pressure_history]
            
            # Calculate volatility
            if len(imbalances) > 1:
                mean_imbalance = sum(imbalances) / len(imbalances)
                variance = sum((x - mean_imbalance) ** 2 for x in imbalances) / len(imbalances)
                volatility = variance ** 0.5
            else:
                volatility = 0.0
            
            # Determine stability
            if volatility < 0.05:
                stability = "STABLE"
            elif volatility < 0.15:
                stability = "MODERATE"
            else:
                stability = "VOLATILE"
            
            # Calculate trend consistency
            directions = [p["direction"] if "direction" in p else "NEUTRAL" for p in pressure_history]
            buy_count = sum(1 for d in directions if "BUY" in d)
            sell_count = sum(1 for d in directions if "SELL" in d)
            total_count = len(directions)
            
            if total_count > 0:
                trend_consistency = max(buy_count, sell_count) / total_count
            else:
                trend_consistency = 0.0
            
            return {
                "stability": stability,
                "volatility": volatility,
                "trend_consistency": trend_consistency,
                "sample_size": len(pressure_history)
            }
            
        except Exception as e:
            logger.error(f"❌ Pressure stability analysis failed: {e}")
            return {
                "stability": "UNKNOWN",
                "volatility": 0.0,
                "trend_consistency": 0.0
            }
