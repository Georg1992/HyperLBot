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
        pass
    
    def analyze_sentiment_conditions(self, raw_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze sentiment conditions for trading suitability
        
        NEW: raw_data parameter contains pre-fetched Fear & Greed data.
        If provided, uses it instead of fetching from API.
        
        Args:
            raw_data: Pre-fetched raw API data containing "fear_greed" key (all mandatory - NO FALLBACKS)
        """
        try:
            factors = []
            risk_factors = []
            positive_factors = []
            
            # Use pre-fetched fear & greed data (all data is mandatory - NO FALLBACKS)
            if not raw_data or "fear_greed" not in raw_data:
                raise ValueError("raw_data with 'fear_greed' key is required (NO FALLBACKS)")
            fear_greed_data = raw_data["fear_greed"]
            if fear_greed_data is None:
                raise ValueError("Pre-fetched fear_greed data is None (NO FALLBACKS)")
            # Validate required keys (NO FALLBACKS)
            if "index_value" not in fear_greed_data:
                raise ValueError("Fear & Greed data missing 'index_value' key (NO FALLBACKS)")
            
            # Handle both "index_value" (from API) and "value" (legacy) keys
            if "index_value" in fear_greed_data:
                fear_greed_value = fear_greed_data["index_value"]
            elif "value" in fear_greed_data:
                fear_greed_value = fear_greed_data["value"]
            else:
                raise ValueError("Fear & Greed data missing both 'index_value' and 'value' keys (NO FALLBACKS)")
            
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
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
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
