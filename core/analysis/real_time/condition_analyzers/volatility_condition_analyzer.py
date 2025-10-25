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
        logger.debug("VolatilityConditionAnalyzer initialized")
    
    def analyze_volatility_conditions(self, volatility_5m: float, volatility_category: str) -> Dict[str, Any]:
        """Analyze volatility conditions using existing VolatilityCalculator - NO DUPLICATION"""
        try:
            # Use existing VolatilityCalculator instead of duplicating logic
            from core.calculations.volatility_calculator import create_volatility_calculator
            volatility_calculator = create_volatility_calculator("BTC")
            volatility_analysis = volatility_calculator.get_latest_analysis()
            
            # Extract data from existing calculator
            level = volatility_analysis.get("level", "UNKNOWN")
            suitable_for_trading = volatility_analysis.get("suitable_for_trading", False)
            risk_level = volatility_analysis.get("risk_level", "UNKNOWN")
            recommendations = volatility_analysis.get("recommendations", [])
            
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
