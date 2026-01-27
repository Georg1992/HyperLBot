#!/usr/bin/env python3
"""
Whale Condition Analyzer - SRP Compliant
Single Responsibility: Analyze whale conditions for trading suitability
"""

from typing import Dict, Any
from loguru import logger


class WhaleConditionAnalyzer:
    """Analyzes whale conditions - follows SRP"""
    
    # Activity level mapping (very_high and high both map to HIGH_ACCUMULATION)
    _ACTIVITY_LEVEL_MAP = {
        "very_high": "HIGH_ACCUMULATION",
        "high": "HIGH_ACCUMULATION",
        "medium": "NORMAL",
        "low": "LOW"
    }
    
    def analyze_whale_conditions(self, whale_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze whale conditions using PASSED DATA - NO REDUNDANT FETCHING
        
        All data is mandatory - NO FALLBACKS
        """
        try:
            if not whale_data:
                raise ValueError("Whale data is required (NO FALLBACKS)")
            
            # Extract nested data structure - NO FALLBACKS
            whale_activity_dict = whale_data["whale_activity"]
            exchange_flows = whale_data["exchange_flows"]
            sentiment_dict = whale_data["sentiment"]
            
            # Extract values from nested structures
            whale_count = whale_activity_dict["whale_count"]
            activity_level = whale_activity_dict["activity_level"]
            flow_direction = exchange_flows["flow_direction"]
            whale_sentiment = sentiment_dict["classification"]
            
            # Map activity_level to whale_activity string - Required (NO FALLBACKS)
            if activity_level not in self._ACTIVITY_LEVEL_MAP:
                raise ValueError(f"Invalid activity_level '{activity_level}' - must be one of {list(self._ACTIVITY_LEVEL_MAP.keys())} (NO FALLBACKS)")
            whale_activity = self._ACTIVITY_LEVEL_MAP[activity_level]
            
            # Convert to condition analyzer format
            factors = [f"Whale Activity: {whale_activity}"]
            risk_factors = []
            positive_factors = []
            
            # Analyze whale activity
            if whale_activity == "HIGH_ACCUMULATION":
                risk_factors.append("High whale accumulation detected")
                factors.append("Whales accumulating - potential price pressure")
            elif whale_activity == "HIGH_DISTRIBUTION":
                risk_factors.append("High whale distribution detected")
                factors.append("Whales distributing - potential selling pressure")
            elif whale_activity == "NORMAL":
                positive_factors.append("Normal whale activity")
                factors.append("Whale activity within normal range")
            elif whale_activity == "LOW":
                positive_factors.append("Low whale activity - stable conditions")
                factors.append("Minimal whale activity")
            
            # Analyze exchange flows
            if flow_direction in ["strong_outflow", "outflow"]:
                risk_factors.append(f"Whale outflow detected: {flow_direction}")
                factors.append("Whales moving funds out - potential selling pressure")
            elif flow_direction in ["strong_inflow", "inflow"]:
                positive_factors.append(f"Whale inflow detected: {flow_direction}")
                factors.append("Whales moving funds in - potential buying pressure")
            
            # Analyze whale sentiment
            if whale_sentiment == "BULLISH":
                positive_factors.append("Whale sentiment bullish")
            elif whale_sentiment == "BEARISH":
                risk_factors.append("Whale sentiment bearish")
            
            # Analyze whale count
            if whale_count > 50:
                risk_factors.append(f"High whale count: {whale_count}")
            elif whale_count > 20:
                factors.append(f"Moderate whale activity: {whale_count}")
            else:
                positive_factors.append(f"Low whale count: {whale_count}")
            
            # Determine trading suitability
            suitable_for_trading = whale_activity in ["NORMAL", "LOW"] and whale_sentiment != "BEARISH"
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "whale_activity": whale_activity,
                "whale_count": whale_count,
                "whale_sentiment": whale_sentiment,
                "exchange_flows": exchange_flows,
                "suitable_for_trading": suitable_for_trading,
                "whale_data": whale_data  # Include raw data for dashboard
            }
        except Exception as e:
            logger.error(f"❌ Whale condition analysis failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
