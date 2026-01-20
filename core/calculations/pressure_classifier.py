#!/usr/bin/env python3
"""
Pressure Classifier Module
Classifies pressure levels and determines trading implications
"""

import time
from typing import Dict, List, Any
from loguru import logger


class PressureClassifier:
    """
    Classifies pressure levels and determines trading implications.
    Handles pressure categorization and trading recommendations.
    """
    
    def __init__(self):
        logger.debug("📊 PressureClassifier initialized")
    
    def classify_pressure_level(self, direction: str, strength: float, confidence: float) -> Dict[str, Any]:
        """
        Classify pressure into levels based on direction, strength, and confidence.
        
        Args:
            direction: Pressure direction
            strength: Pressure strength (0-1)
            confidence: Analysis confidence (0-1)
        
        Returns:
            Dictionary with pressure classification
        """
        try:
            # Determine overall level
            if strength > 0.8 and confidence > 0.7:
                level = "VERY_STRONG"
                description = f"Very strong {direction.lower()} pressure with high confidence"
            elif strength > 0.6 and confidence > 0.5:
                level = "STRONG"
                description = f"Strong {direction.lower()} pressure"
            elif strength > 0.4 and confidence > 0.3:
                level = "MODERATE"
                description = f"Moderate {direction.lower()} pressure"
            elif strength > 0.2:
                level = "WEAK"
                description = f"Weak {direction.lower()} pressure"
            else:
                level = "NEUTRAL"
                description = "Neutral pressure - no clear direction"
            
            return {
                "level": level,
                "description": description,
                "direction": direction,
                "strength": strength,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"❌ Pressure classification failed: {e}")
            return {
                "level": "UNKNOWN",
                "description": "Classification failed",
                "direction": direction,
                "strength": strength,
                "confidence": confidence
            }
    
    def determine_trading_implications(self, classification: Dict[str, Any], trend: str) -> Dict[str, Any]:
        """
        Determine trading implications based on pressure analysis.
        
        Args:
            classification: Pressure classification results
            trend: Pressure trend direction
        
        Returns:
            Dictionary with trading implications
        """
        try:
            level = classification["level"] if "level" in classification else "UNKNOWN"
            direction = classification["direction"] if "direction" in classification else "NEUTRAL"
            strength = classification["strength"] if "strength" in classification else 0.0
            confidence = classification["confidence"] if "confidence" in classification else 0.0
            
            implications = []
            risk_level = "MEDIUM"
            trading_suitability = True
            
            # Level-based implications
            if level == "VERY_STRONG":
                implications.extend([
                    "Exceptional pressure detected",
                    "High probability of significant price movement",
                    "Consider aggressive position sizing"
                ])
                risk_level = "HIGH"
            elif level == "STRONG":
                implications.extend([
                    "Strong pressure detected",
                    "Good probability of price movement",
                    "Standard position sizing appropriate"
                ])
                risk_level = "MEDIUM"
            elif level == "MODERATE":
                implications.extend([
                    "Moderate pressure detected",
                    "Some price movement expected",
                    "Conservative position sizing recommended"
                ])
                risk_level = "MEDIUM"
            elif level == "WEAK":
                implications.extend([
                    "Weak pressure detected",
                    "Limited price movement expected",
                    "Consider waiting for stronger signals"
                ])
                risk_level = "LOW"
            else:  # NEUTRAL or UNKNOWN
                implications.extend([
                    "No clear pressure direction",
                    "Uncertain price movement",
                    "Avoid new positions until clarity"
                ])
                risk_level = "LOW"
                trading_suitability = False
            
            # Direction-based implications
            if direction in ["STRONG_BUY", "BUY"]:
                implications.append("Bullish pressure - consider long positions")
            elif direction in ["STRONG_SELL", "SELL"]:
                implications.append("Bearish pressure - consider short positions")
            
            # Trend-based implications
            if trend == "BULLISH":
                implications.append("Bullish trend confirmed by pressure")
            elif trend == "BEARISH":
                implications.append("Bearish trend confirmed by pressure")
            elif trend == "MIXED":
                implications.append("Mixed signals - use caution")
            
            return {
                "implications": implications,
                "risk_level": risk_level,
                "trading_suitability": trading_suitability,
                "pressure_level": level,
                "pressure_direction": direction,
                "trend": trend
            }
            
        except Exception as e:
            logger.error(f"❌ Trading implications determination failed: {e}")
            return {
                "implications": ["Analysis failed - use caution"],
                "risk_level": "UNKNOWN",
                "trading_suitability": False,
                "pressure_level": "UNKNOWN",
                "pressure_direction": "UNKNOWN",
                "trend": "UNKNOWN"
            }
    
    def get_pressure_recommendations(self, classification: Dict[str, Any], implications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get trading recommendations based on pressure analysis.
        
        Args:
            classification: Pressure classification results
            implications: Trading implications
        
        Returns:
            Dictionary with trading recommendations
        """
        try:
            recommendations = []
            level = classification["level"] if "level" in classification else "UNKNOWN"
            direction = classification["direction"] if "direction" in classification else "NEUTRAL"
            trading_suitability = implications["trading_suitability"] if "trading_suitability" in implications else False
            
            # General recommendations based on level
            if level == "VERY_STRONG":
                recommendations.extend([
                    "High confidence trade opportunity",
                    "Consider larger position sizes",
                    "Monitor for pressure exhaustion"
                ])
            elif level == "STRONG":
                recommendations.extend([
                    "Good trade opportunity",
                    "Standard position sizing",
                    "Set appropriate stop losses"
                ])
            elif level == "MODERATE":
                recommendations.extend([
                    "Moderate trade opportunity",
                    "Conservative position sizing",
                    "Use tight stop losses"
                ])
            elif level == "WEAK":
                recommendations.extend([
                    "Weak trade opportunity",
                    "Small position sizes only",
                    "Wait for stronger signals"
                ])
            else:
                recommendations.extend([
                    "No clear trading opportunity",
                    "Avoid new positions",
                    "Wait for pressure to develop"
                ])
            
            # Direction-specific recommendations
            if direction in ["STRONG_BUY", "BUY"] and trading_suitability:
                recommendations.extend([
                    "Consider long positions",
                    "Look for bullish price action confirmation",
                    "Set stop loss below recent support"
                ])
            elif direction in ["STRONG_SELL", "SELL"] and trading_suitability:
                recommendations.extend([
                    "Consider short positions",
                    "Look for bearish price action confirmation",
                    "Set stop loss above recent resistance"
                ])
            
            # Risk management recommendations
            risk_level = implications.get("risk_level", "MEDIUM")
            if risk_level == "HIGH":
                recommendations.append("High risk - use strict risk management")
            elif risk_level == "LOW":
                recommendations.append("Low risk - standard risk management")
            
            return {
                "recommendations": recommendations,
                "recommendation_count": len(recommendations),
                "pressure_level": level,
                "pressure_direction": direction,
                "trading_suitability": trading_suitability
            }
            
        except Exception as e:
            logger.error(f"❌ Pressure recommendations failed: {e}")
            return {
                "recommendations": ["Analysis failed - use caution"],
                "recommendation_count": 1,
                "pressure_level": "UNKNOWN",
                "pressure_direction": "UNKNOWN",
                "trading_suitability": False
            }
