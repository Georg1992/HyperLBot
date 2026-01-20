#!/usr/bin/env python3
"""
Fear & Greed Index API Client
=============================
Fetches market sentiment data from the Fear & Greed Index API
Provides critical sentiment signals for BTC trading decisions

API Source: https://alternative.me/crypto/api/
Free, unlimited calls, no API key required
"""

import time
import requests
from typing import Dict, Any, List, Optional, Tuple, Callable
from loguru import logger
from datetime import datetime, timedelta


class FearGreedAPI:
    """
    Fear & Greed Index fetcher for market sentiment analysis
    Provides critical sentiment signals for BTC trading decisions
    """
    
    def __init__(self):
        self.api_url = "https://api.alternative.me/fng/"
        
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        logger.info("😨 Fear & Greed Index Fetcher initialized - Market sentiment analysis")
    
    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get current Fear & Greed Index value and classification
        
        Returns:
            Dict containing index value, classification, and sentiment signals
        """
        try:
            # Use centralized cache with get_or_set pattern
            cache_key = "fear_greed_index"
            
            def fetch_fresh_fear_greed():
                # Use actual Fear & Greed Index API from alternative.me
                logger.info("📊 Fetching Fear & Greed data from alternative.me API")
                
                try:
                    response = requests.get("https://api.alternative.me/fng/", timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if "data" in data and data["data"] and len(data["data"]) > 0:
                        fng_data = data["data"][0]
                        
                        # Parse the Fear & Greed data
                        index_value = int(fng_data["value"])
                        classification = fng_data["value_classification"]
                        
                        # Convert to our format
                        fear_greed_data = {
                            'index_value': index_value,
                            'sentiment': classification.upper().replace(" ", "_"),
                            'timestamp': int(fng_data["timestamp"]),
                            'data_source': 'alternative.me_fng',
                            'confidence': 0.9,  # High confidence from official API
                            'sentiment_signals': self._generate_sentiment_signals(index_value, classification)
                        }
                        
                        logger.success(f"✅ Fear & Greed Index: {index_value} ({classification})")
                        return fear_greed_data
                    else:
                        logger.warning("⚠️ No Fear & Greed data returned from API")
                        raise ValueError("Real Fear & Greed data not available - NO FALLBACKS")
                        
                except requests.RequestException as e:
                    logger.error(f"❌ Failed to fetch Fear & Greed data from API: {e}")
                    raise ValueError(f"Real Fear & Greed data not available - NO FALLBACKS: {e}")
            
            # Get from cache or fetch fresh
            fear_greed_data = self._cache.get_or_set(
                key=cache_key,
                factory_func=fetch_fresh_fear_greed,
                # Use CentralizedCache TTL instead of hardcoded value
                force_fresh=False
            )
            
            return fear_greed_data
                
        except Exception as e:
            logger.error(f"❌ Fear & Greed Index fetch failed: {e}")
            raise ValueError(f"Real Fear & Greed data not available - NO FALLBACKS: {e}")
    
    def _generate_sentiment_signals(self, index_value: int, classification: str) -> Dict[str, Any]:
        """
        Generate trading signals based on Fear & Greed Index
        
        Args:
            index_value: Current index value (0-100)
            classification: Text classification (e.g., "Extreme Fear", "Greed")
        
        Returns:
            Dict containing sentiment signals for trading decisions
        """
        try:
            # Define sentiment zones
            extreme_fear = index_value <= 25
            extreme_greed = index_value > 75
            
            # Generate trading signals
            signals = {
                "market_sentiment": classification,
                "sentiment_zone": self._get_sentiment_zone(index_value),
                "trading_bias": self._get_trading_bias(index_value),
                "confidence_boost": self._get_confidence_boost(index_value),
                "risk_level": self._get_risk_level(index_value),
                "reversal_probability": self._get_reversal_probability(index_value),
                "recommended_action": self._get_recommended_action(index_value)
            }
            
            # Add specific signals for extreme conditions
            if extreme_fear:
                signals.update({
                    "extreme_condition": True,
                    "buy_signal_strength": "STRONG",
                    "market_oversold": True,
                    "reversal_imminent": True
                })
            elif extreme_greed:
                signals.update({
                    "extreme_condition": True,
                    "sell_signal_strength": "STRONG", 
                    "market_overbought": True,
                    "reversal_imminent": True
                })
            else:
                signals.update({
                    "extreme_condition": False,
                    "buy_signal_strength": "WEAK",
                    "sell_signal_strength": "WEAK",
                    "market_oversold": False,
                    "market_overbought": False,
                    "reversal_imminent": False
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Sentiment signal generation failed: {e}")
            return self._get_default_signals()
    
    def _get_sentiment_zone(self, index_value: int) -> str:
        """Get sentiment zone based on index value"""
        if index_value <= 25:
            return "EXTREME_FEAR"
        elif index_value <= 45:
            return "FEAR"
        elif index_value <= 55:
            return "NEUTRAL"
        elif index_value <= 75:
            return "GREED"
        else:
            return "EXTREME_GREED"
    
    def _get_trading_bias(self, index_value: int) -> str:
        """Get trading bias based on sentiment"""
        if index_value <= 25:
            return "STRONG_BUY"  # Extreme fear = buying opportunity
        elif index_value <= 45:
            return "WEAK_BUY"
        elif index_value <= 55:
            return "NEUTRAL"
        elif index_value <= 75:
            return "WEAK_SELL"
        else:
            return "STRONG_SELL"  # Extreme greed = selling opportunity
    
    def _get_confidence_boost(self, index_value: int) -> float:
        """Get confidence boost for predictions based on sentiment"""
        if index_value <= 25 or index_value >= 75:
            return 0.15  # 15% confidence boost for extreme conditions
        elif index_value <= 35 or index_value >= 65:
            return 0.10  # 10% confidence boost for strong sentiment
        elif index_value <= 45 or index_value >= 55:
            return 0.05  # 5% confidence boost for moderate sentiment
        else:
            return 0.0  # No boost for neutral sentiment
    
    def _get_risk_level(self, index_value: int) -> str:
        """Get risk level based on sentiment"""
        if index_value <= 25 or index_value >= 75:
            return "HIGH"  # Extreme conditions = high risk/reward
        elif index_value <= 35 or index_value >= 65:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_reversal_probability(self, index_value: int) -> float:
        """Get probability of market reversal based on sentiment"""
        if index_value <= 25 or index_value >= 75:
            return 0.75  # 75% chance of reversal in extreme conditions
        elif index_value <= 35 or index_value >= 65:
            return 0.60  # 60% chance of reversal in strong sentiment
        elif index_value <= 45 or index_value >= 55:
            return 0.45  # 45% chance of reversal in moderate sentiment
        else:
            return 0.30  # 30% chance of reversal in neutral sentiment
    
    def _get_recommended_action(self, index_value: int) -> str:
        """Get recommended trading action based on sentiment"""
        if index_value <= 25:
            return "AGGRESSIVE_BUY"
        elif index_value <= 35:
            return "MODERATE_BUY"
        elif index_value <= 45:
            return "CAUTIOUS_BUY"
        elif index_value <= 55:
            return "NEUTRAL"
        elif index_value <= 65:
            return "CAUTIOUS_SELL"
        elif index_value <= 75:
            return "MODERATE_SELL"
        else:
            return "AGGRESSIVE_SELL"
    
    
    def _get_default_data(self) -> Dict[str, Any]:
        """Get default data when API fails"""
        # NO FALLBACKS - Real Fear & Greed data not available
        raise ValueError("Real Fear & Greed data not available - NO FALLBACKS")
    
    # _get_default_signals method removed - NO FALLBACKS policy
    
    def test_connection(self) -> bool:
        """Test connection to Fear & Greed API"""
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and data["data"]:
                    logger.success("✅ Fear & Greed API connection successful")
                    return True
            
            logger.error("❌ Fear & Greed API connection failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Fear & Greed API test error: {e}")
            return False


# Global instance for consistent usage across the codebase
# Singleton pattern implementation
_global_fear_greed_api = None

def get_global_fear_greed_api() -> FearGreedAPI:
    """Get the global FearGreedAPI singleton instance"""
    global _global_fear_greed_api
    if _global_fear_greed_api is None:
        _global_fear_greed_api = FearGreedAPI()
    return _global_fear_greed_api

# Backward compatibility
fear_greed_api = get_global_fear_greed_api()


def main():
    """Test the Fear & Greed Index fetcher"""
    logger.info("🔍 Testing Fear & Greed Index Fetcher")
    logger.info("=" * 50)
    
    fetcher = FearGreedFetcher()
    
    # Test connection
    if not fetcher.test_connection():
        logger.error("❌ Cannot connect to Fear & Greed API")
        return
    
    # Test data fetching
    logger.info("📊 Testing Fear & Greed data fetching...")
    data = fetcher.get_fear_greed_index()
    
    if data and "error" not in data:
        logger.success("✅ Fear & Greed data fetched successfully!")
        logger.info(f"Index Value: {data['index_value']}")
        logger.info(f"Classification: {data['classification']}")
        logger.info(f"Sentiment Zone: {data['sentiment_signals']['sentiment_zone']}")
        logger.info(f"Trading Bias: {data['sentiment_signals']['trading_bias']}")
        logger.info(f"Recommended Action: {data['sentiment_signals']['recommended_action']}")
        logger.info(f"Confidence Boost: {data['sentiment_signals']['confidence_boost']:.1%}")
        logger.info(f"Reversal Probability: {data['sentiment_signals']['reversal_probability']:.1%}")
    else:
        logger.error("❌ Failed to fetch Fear & Greed data")


if __name__ == "__main__":
    main()
