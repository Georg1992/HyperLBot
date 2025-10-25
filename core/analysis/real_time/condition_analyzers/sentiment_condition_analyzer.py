#!/usr/bin/env python3
"""
Sentiment Condition Analyzer - SRP Compliant
Single Responsibility: Analyze sentiment conditions for trading suitability
"""

from typing import Dict, Any
from loguru import logger


class SentimentConditionAnalyzer:
    """Analyzes sentiment conditions - follows SRP"""
    
    def __init__(self):
        logger.debug("SentimentConditionAnalyzer initialized")
    
    def analyze_sentiment_conditions(self) -> Dict[str, Any]:
        """Analyze sentiment conditions for trading suitability"""
        try:
            factors = []
            risk_factors = []
            positive_factors = []
            
            # Get fear & greed data
            fear_greed_data = self._get_fear_greed_data()
            fear_greed_value = fear_greed_data.get("value", 50)
            
            # Analyze fear & greed levels
            if fear_greed_value <= 20:
                risk_factors.append("Extreme fear in market")
                factors.append("Market in extreme fear")
            elif fear_greed_value <= 30:
                risk_factors.append("High fear in market")
                factors.append("Market showing high fear")
            elif fear_greed_value >= 80:
                risk_factors.append("Extreme greed in market")
                factors.append("Market in extreme greed")
            elif fear_greed_value >= 70:
                risk_factors.append("High greed in market")
                factors.append("Market showing high greed")
            else:
                positive_factors.append("Balanced sentiment")
                factors.append("Market sentiment balanced")
            
            return {
                "factors": factors,
                "risk_factors": risk_factors,
                "positive_factors": positive_factors,
                "sentiment_level": self._classify_sentiment(fear_greed_value),
                "fear_greed_value": fear_greed_value,
                "suitable_for_trading": 30 <= fear_greed_value <= 70,
                "sentiment_data": fear_greed_data  # Include raw data for dashboard
            }
        except Exception as e:
            logger.error(f"❌ Sentiment condition analysis failed: {e}")
            return {
                "factors": ["Sentiment analysis failed"],
                "risk_factors": ["Analysis error"],
                "positive_factors": [],
                "sentiment_level": "UNKNOWN",
                "fear_greed_value": 50,
                "suitable_for_trading": False
            }
    
    def _get_fear_greed_data(self) -> Dict[str, Any]:
        """Get fear & greed data"""
        try:
            from core.external.fear_greed_api import FearGreedAPI
            fear_greed_api = FearGreedAPI()
            return fear_greed_api.get_fear_greed_index()
        except Exception as e:
            logger.error(f"❌ Failed to get fear & greed data: {e}")
            return {"value": 50, "classification": "NEUTRAL"}
    
    def _classify_sentiment(self, value: int) -> str:
        """Classify sentiment level"""
        if value <= 20:
            return "EXTREME_FEAR"
        elif value <= 30:
            return "FEAR"
        elif value <= 40:
            return "FEARFUL"
        elif value <= 60:
            return "NEUTRAL"
        elif value <= 70:
            return "GREEDY"
        elif value <= 80:
            return "GREED"
        else:
            return "EXTREME_GREED"
