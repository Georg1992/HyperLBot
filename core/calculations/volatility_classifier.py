#!/usr/bin/env python3
"""
Volatility Classifier Module
Classifies volatility levels and determines trading suitability
"""

import time
from typing import Dict, List, Any
from loguru import logger


class VolatilityClassifier:
    """
    Classifies volatility levels and determines trading conditions.
    Handles threshold analysis and trading suitability decisions.
    """
    
    def __init__(self):
        # Universal volatility thresholds (not strategy-specific)
        self.thresholds = {
            "LOW": 0.0015,
            "MODERATE": 0.0030, 
            "HIGH": 0.0060,
            "EXTREME": 0.0060
        }
        logger.debug("📊 VolatilityClassifier initialized")
    
    def classify_volatility_level(self, volatility: float) -> Dict[str, Any]:
        """
        Classify volatility into levels (LOW, MODERATE, HIGH, EXTREME).
        
        Args:
            volatility: Volatility value to classify
        
        Returns:
            Dictionary with classification results
        """
        try:
            if volatility <= self.thresholds["LOW"]:
                level = "LOW"
                description = "Low volatility - stable market conditions"
            elif volatility <= self.thresholds["MODERATE"]:
                level = "MODERATE"
                description = "Moderate volatility - normal market conditions"
            elif volatility <= self.thresholds["HIGH"]:
                level = "HIGH"
                description = "High volatility - increased market activity"
            else:
                level = "EXTREME"
                description = "Extreme volatility - very high market activity"
            
            return {
                "level": level,
                "description": description,
                "volatility": volatility,
                "thresholds": self.thresholds.copy()
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility classification failed: {e}")
            return {
                "level": "UNKNOWN",
                "description": "Classification failed",
                "volatility": volatility,
                "thresholds": self.thresholds.copy()
            }
    
    def determine_trading_suitability(self, volatility: float, level: str) -> Dict[str, Any]:
        """
        Determine if market conditions are suitable for trading.
        
        Args:
            volatility: Current volatility value
            level: Volatility level classification
        
        Returns:
            Dictionary with trading suitability analysis
        """
        try:
            # Trading suitability based on volatility levels
            if level == "LOW":
                suitable = True
                reason = "Low volatility provides stable trading conditions"
                risk_level = "LOW"
            elif level == "MODERATE":
                suitable = True
                reason = "Moderate volatility offers good trading opportunities"
                risk_level = "MEDIUM"
            elif level == "HIGH":
                suitable = True
                reason = "High volatility provides opportunities but requires careful risk management"
                risk_level = "HIGH"
            else:  # EXTREME
                suitable = False
                reason = "Extreme volatility creates unpredictable market conditions"
                risk_level = "EXTREME"
            
            return {
                "suitable_for_trading": suitable,
                "reason": reason,
                "risk_level": risk_level,
                "volatility_level": level,
                "volatility_value": volatility
            }
            
        except Exception as e:
            logger.error(f"❌ Trading suitability determination failed: {e}")
            return {
                "suitable_for_trading": False,
                "reason": "Analysis failed",
                "risk_level": "UNKNOWN",
                "volatility_level": level,
                "volatility_value": volatility
            }
    
    def get_volatility_recommendations(self, volatility: float, level: str) -> Dict[str, Any]:
        """
        Get trading recommendations based on volatility analysis.
        
        Args:
            volatility: Current volatility value
            level: Volatility level classification
        
        Returns:
            Dictionary with trading recommendations
        """
        try:
            recommendations = []
            
            if level == "LOW":
                recommendations.extend([
                    "Consider range trading strategies",
                    "Monitor for breakout opportunities",
                    "Use tighter stop losses due to low volatility"
                ])
            elif level == "MODERATE":
                recommendations.extend([
                    "Standard trading strategies work well",
                    "Monitor trend continuation patterns",
                    "Use normal risk management"
                ])
            elif level == "HIGH":
                recommendations.extend([
                    "Use wider stop losses",
                    "Consider position sizing adjustments",
                    "Monitor for trend reversals"
                ])
            else:  # EXTREME
                recommendations.extend([
                    "Avoid new positions",
                    "Consider reducing position sizes",
                    "Wait for volatility to decrease"
                ])
            
            return {
                "recommendations": recommendations,
                "volatility_level": level,
                "volatility_value": volatility,
                "recommendation_count": len(recommendations)
            }
            
        except Exception as e:
            logger.error(f"❌ Volatility recommendations failed: {e}")
            return {
                "recommendations": ["Analysis failed - use caution"],
                "volatility_level": level,
                "volatility_value": volatility,
                "recommendation_count": 1
            }
