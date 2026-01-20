#!/usr/bin/env python3
"""
Whale Condition Analyzer - SRP Compliant
Single Responsibility: Analyze whale conditions for trading suitability
"""

from typing import Dict, Any
from loguru import logger


class WhaleConditionAnalyzer:
    """Analyzes whale conditions - follows SRP"""
    
    def __init__(self):
        pass
    
    def analyze_whale_conditions(self, whale_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze whale conditions using PASSED DATA - NO REDUNDANT FETCHING"""
        try:
            # This analyzer should receive whale data as parameter from caller
            # For now, return minimal analysis since whale data should be passed in
            if not whale_data:
                # Minimal response when no data provided
                return {
                    "factors": ["Whale data not available"],
                    "risk_factors": [],
                    "positive_factors": [],
                    "whale_activity": "UNKNOWN",
                    "whale_count": 0,
                    "whale_sentiment": "UNKNOWN"
                }
            
            # Use passed data
            whale_activity = whale_data.get("whale_activity", "UNKNOWN")
            whale_count = whale_data.get("whale_count", 0)
            whale_sentiment = whale_data.get("whale_sentiment", "NEUTRAL")
            exchange_flows = whale_data.get("exchange_flows", {})
            
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
            return {
                "factors": ["Whale analysis failed"],
                "risk_factors": ["Analysis error"],
                "positive_factors": [],
                "whale_activity": "UNKNOWN",
                "whale_count": 0,
                "suitable_for_trading": False
            }
    
