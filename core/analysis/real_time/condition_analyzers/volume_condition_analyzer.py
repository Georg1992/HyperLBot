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
        pass
    
    def analyze_volume_conditions(self, volume_category: str) -> Dict[str, Any]:
        """Analyze volume conditions using PASSED DATA - NO REDUNDANT FETCHING"""
        try:
            # Use passed parameter directly - data already fetched once
            category = volume_category
            
            # Determine suitability and risk from category
            suitable_for_trading = category in ["NORMAL", "HIGH", "VERY_HIGH"]
            risk_level = "LOW" if suitable_for_trading else "HIGH"
            
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
                "suitable_for_trading": suitable_for_trading
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
