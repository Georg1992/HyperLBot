#!/usr/bin/env python3
"""
Volatility Condition Analyzer - SRP Compliant
Single Responsibility: Analyze volatility conditions for trading suitability
"""

from typing import Dict, Any
from loguru import logger


class VolatilityConditionAnalyzer:
    """Analyzes volatility conditions - follows SRP"""
    
    def __init__(self):
        pass
    
    def analyze_volatility_conditions(self, volatility_5m: float, volatility_category: str) -> Dict[str, Any]:
        """Analyze volatility conditions using PASSED DATA - NO REDUNDANT FETCHING"""
        try:
            # Use passed parameters directly - data already fetched once in market_data_service
            # NO redundant calculator creation!
            level = volatility_category
            
            # Determine suitability based on category
            suitable_for_trading = volatility_category in ["LOW", "MODERATE", "HIGH"]
            risk_level = {
                "VERY_LOW": "LOW",
                "LOW": "LOW", 
                "MODERATE": "MEDIUM",
                "HIGH": "HIGH",
                "EXTREME": "VERY_HIGH"
            }.get(volatility_category, "UNKNOWN")
            
            recommendations = []
            if volatility_category == "EXTREME":
                recommendations.append("Reduce position size")
            elif volatility_category == "VERY_LOW":
                recommendations.append("Widen stop losses")
            
            # Convert to condition analyzer format
            factors = [f"Volatility: {level}"]
            risk_factors = []
            positive_factors = []
            
            if not suitable_for_trading:
                risk_factors.append(f"Volatility unsuitable for trading: {level}")
            else:
                positive_factors.append(f"Volatility suitable for trading: {level}")
            
            if risk_level == "HIGH":
                risk_factors.append("High volatility risk")
            elif risk_level == "LOW":
                positive_factors.append("Low volatility risk")
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "volatility_level": level,
                "volatility_value": volatility_5m,
                "suitable_for_trading": suitable_for_trading,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"❌ Volatility condition analysis failed: {e}")
            return {
                "factors": ["Volatility analysis failed"],
                "risk_factors": ["Analysis error"],
                "positive_factors": [],
                "volatility_level": "UNKNOWN",
                "volatility_value": volatility_5m,
                "suitable_for_trading": False
            }
