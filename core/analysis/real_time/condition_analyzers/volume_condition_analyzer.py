#!/usr/bin/env python3
"""
Volume Condition Analyzer - SRP Compliant
Single Responsibility: Analyze volume conditions for trading suitability
"""

from typing import Dict, Any
from loguru import logger


class VolumeConditionAnalyzer:
    """Analyzes volume conditions - follows SRP"""
    
    def __init__(self):
        # Removed excessive debug logging
        pass
    
    def analyze_volume_conditions(self, volume_category: str) -> Dict[str, Any]:
        """Analyze volume conditions using existing VolumeCalculator - NO DUPLICATION"""
        try:
            # Use existing VolumeCalculator instead of duplicating logic
            from core.calculations.volume_calculator import create_volume_calculator
            volume_calculator = create_volume_calculator("BTC")
            volume_analysis = volume_calculator.get_latest_analysis()
            
            # Extract data from existing calculator
            category = volume_analysis["volume_category"] if "volume_category" in volume_analysis else "UNKNOWN"
            implications = volume_analysis["volume_implications"] if "volume_implications" in volume_analysis else {}
            recommendations = volume_analysis["volume_recommendations"] if "volume_recommendations" in volume_analysis else []
            suitable_for_trading = implications["trading_suitable"] if "trading_suitable" in implications else False
            risk_level = implications["risk_level"] if "risk_level" in implications else "UNKNOWN"
            
            # Convert to condition analyzer format
            factors = [f"Volume: {category}"]
            risk_factors = []
            positive_factors = []
            
            if not suitable_for_trading:
                risk_factors.append(f"Volume unsuitable for trading: {category}")
            else:
                positive_factors.append(f"Volume suitable for trading: {category}")
            
            if risk_level == "HIGH":
                risk_factors.append("High volume risk")
            elif risk_level == "LOW":
                positive_factors.append("Low volume risk")
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "volume_level": category,
                "suitable_for_trading": suitable_for_trading,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"❌ Volume condition analysis failed: {e}")
            return {
                "factors": ["Volume analysis failed"],
                "risk_factors": ["Analysis error"],
                "positive_factors": [],
                "volume_level": "UNKNOWN",
                "suitable_for_trading": False
            }
