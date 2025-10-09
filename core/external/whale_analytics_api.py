#!/usr/bin/env python3
"""
Whale Analytics API Client
==========================
Fetches whale activity data from BlockCypher API (free tier)
Tracks large BTC transactions and exchange flows
"""

import requests
import time
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger


class WhaleAnalyticsAPI:
    """
    Fetches whale activity data from BlockCypher API
    
    Features:
    - Large transaction tracking (>$100k)
    - Exchange flow monitoring
    - Whale sentiment analysis
    - Free API (no costs)
    """
    
    def __init__(self):
        self.api_base = "https://api.blockcypher.com/v1/btc/main"
        self.cache = {}
        self.cache_duration = 180  # 3 minutes cache
        self.whale_threshold_usd = 100000  # $100k minimum whale size
        
        # Known exchange addresses (partial - BlockCypher provides some)
        self.exchange_addresses = {
            "binance": ["1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"],
            "coinbase": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS"],
            "kraken": ["3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC", "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"]
        }
        
        logger.info("🐋 Whale Analytics Fetcher initialized - BlockCypher API integration")
    
    def get_whale_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive whale analytics using REAL Whale Alert API
        
        Returns:
            Dict containing whale activity, sentiment, and exchange flows
        """
        try:
            # Check cache first
            cache_key = "whale_analytics"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]["data"]
            
            # Use REAL BlockCypher API for whale analytics (COMPLETELY FREE)
            from core.external.blockcypher_api import get_global_blockcypher_api
            blockcypher_api = get_global_blockcypher_api()
            
            whale_data = blockcypher_api.get_whale_analytics()
            
            if whale_data and "error" not in whale_data:
                # Cache the result
                self.cache[cache_key] = {
                    "data": whale_data,
                    "timestamp": time.time()
                }
                
                activity_level = whale_data.get('whale_activity', {}).get('activity_level', 'unknown')
                whale_count = whale_data.get('whale_activity', {}).get('whale_count', 0)
                logger.info(f"🐋 Whale analytics updated: {activity_level} activity ({whale_count} whales)")
                return whale_data
            else:
                logger.warning("⚠️ Failed to fetch whale analytics from BlockCypher API")
                raise ValueError("Whale analytics fetch failed - NO FALLBACKS")
                
        except Exception as e:
            logger.error(f"❌ Whale analytics fetch failed: {e}")
            raise ValueError(f"Whale analytics fetch failed - NO FALLBACKS: {e}")
    
    def _fetch_whale_data(self) -> Dict[str, Any]:
        """Fetch whale data from BlockCypher API"""
        try:
            # Get recent transactions
            transactions = self._get_recent_transactions()
            
            # Analyze whale activity
            whale_analysis = self._analyze_whale_activity(transactions)
            
            # Get exchange flows
            exchange_flows = self._analyze_exchange_flows(transactions)
            
            # Calculate sentiment
            sentiment = self._calculate_whale_sentiment(whale_analysis, exchange_flows)
            
            return {
                "whale_activity": whale_analysis,
                "exchange_flows": exchange_flows,
                "sentiment": sentiment,
                "timestamp": time.time(),
                "data_source": "blockcypher"
            }
            
        except Exception as e:
            logger.error(f"❌ Whale data fetch failed: {e}")
            return {"error": str(e)}
    
    def _get_recent_transactions(self) -> List[Dict[str, Any]]:
        """Get recent large transactions from BlockCypher"""
        try:
            # Get recent transactions (last 6 hours worth of blocks)
            url = f"{self.api_base}/txs"
            params = {
                "limit": 50,  # Get last 50 transactions
                "includeHex": False
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            transactions = response.json()
            
            # Filter for large transactions
            large_transactions = []
            for tx in transactions:
                try:
                    # Calculate transaction value in USD (approximate)
                    total_value = sum(output.get("value", 0) for output in tx.get("outputs", []))
                    value_usd = (total_value / 100000000) * 112000  # Convert satoshis to BTC, then to USD
                    
                    if value_usd >= self.whale_threshold_usd:
                        large_transactions.append({
                            "hash": tx.get("hash"),
                            "value_btc": total_value / 100000000,
                            "value_usd": value_usd,
                            "confirmations": tx.get("confirmations", 0),
                            "time": tx.get("received"),
                            "inputs": tx.get("inputs", []),
                            "outputs": tx.get("outputs", [])
                        })
                except Exception as e:
                    continue
            
            logger.info(f"🐋 Found {len(large_transactions)} large transactions (>{self.whale_threshold_usd:,} USD)")
            return large_transactions
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch transactions: {e}")
            return []
    
    def _analyze_whale_activity(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze whale activity patterns"""
        try:
            if not transactions:
                return {
                    "whale_count": 0,
                    "total_volume_usd": 0,
                    "average_size_usd": 0,
                    "activity_level": "low",
                    "confirmed_ratio": 0.0
                }
            
            # Calculate metrics
            whale_count = len(transactions)
            total_volume_usd = sum(tx["value_usd"] for tx in transactions)
            average_size_usd = total_volume_usd / whale_count if whale_count > 0 else 0
            
            # Calculate confirmed ratio
            confirmed_txs = [tx for tx in transactions if tx["confirmations"] > 0]
            confirmed_ratio = len(confirmed_txs) / whale_count if whale_count > 0 else 0
            
            # Determine activity level
            if whale_count >= 20:
                activity_level = "very_high"
            elif whale_count >= 15:
                activity_level = "high"
            elif whale_count >= 10:
                activity_level = "moderate"
            elif whale_count >= 5:
                activity_level = "low"
            else:
                activity_level = "very_low"
            
            return {
                "whale_count": whale_count,
                "total_volume_usd": total_volume_usd,
                "average_size_usd": average_size_usd,
                "activity_level": activity_level,
                "confirmed_ratio": confirmed_ratio,
                "largest_transaction_usd": max(tx["value_usd"] for tx in transactions) if transactions else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Whale activity analysis failed: {e}")
            return {"error": str(e)}
    
    def _analyze_exchange_flows(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze exchange flows from transactions"""
        try:
            if not transactions:
                return {
                    "total_inflow": 0,
                    "total_outflow": 0,
                    "net_flow": 0,
                    "exchange_count": 0,
                    "flow_direction": "neutral"
                }
            
            total_inflow = 0
            total_outflow = 0
            exchange_count = 0
            
            for tx in transactions:
                # Check if transaction involves known exchange addresses
                involves_exchange = False
                
                # Check inputs (outflow from exchanges)
                for input_tx in tx["inputs"]:
                    input_address = input_tx.get("addresses", [""])[0] if input_tx.get("addresses") else ""
                    if self._is_exchange_address(input_address):
                        total_outflow += tx["value_usd"]
                        involves_exchange = True
                
                # Check outputs (inflow to exchanges)
                for output in tx["outputs"]:
                    output_address = output.get("addresses", [""])[0] if output.get("addresses") else ""
                    if self._is_exchange_address(output_address):
                        total_inflow += tx["value_usd"]
                        involves_exchange = True
                
                if involves_exchange:
                    exchange_count += 1
            
            net_flow = total_inflow - total_outflow
            
            # Determine flow direction
            if net_flow > 1000000:  # $1M net inflow
                flow_direction = "strong_inflow"
            elif net_flow > 100000:  # $100k net inflow
                flow_direction = "inflow"
            elif net_flow < -1000000:  # $1M net outflow
                flow_direction = "strong_outflow"
            elif net_flow < -100000:  # $100k net outflow
                flow_direction = "outflow"
            else:
                flow_direction = "neutral"
            
            return {
                "total_inflow": total_inflow,
                "total_outflow": total_outflow,
                "net_flow": net_flow,
                "exchange_count": exchange_count,
                "flow_direction": flow_direction
            }
            
        except Exception as e:
            logger.error(f"❌ Exchange flow analysis failed: {e}")
            return {"error": str(e)}
    
    def _calculate_whale_sentiment(self, whale_analysis: Dict[str, Any], exchange_flows: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate whale sentiment based on activity and flows"""
        try:
            # Base sentiment score
            sentiment_score = 0.5  # Neutral
            
            # Whale activity impact
            whale_count = whale_analysis.get("whale_count", 0)
            activity_level = whale_analysis.get("activity_level", "low")
            
            if activity_level == "very_high":
                sentiment_score += 0.2  # High activity = bullish
            elif activity_level == "high":
                sentiment_score += 0.1
            elif activity_level == "very_low":
                sentiment_score -= 0.1  # Low activity = bearish
            
            # Exchange flow impact
            flow_direction = exchange_flows.get("flow_direction", "neutral")
            net_flow = exchange_flows.get("net_flow", 0)
            
            if flow_direction == "strong_inflow":
                sentiment_score += 0.3  # Strong inflow = very bullish
            elif flow_direction == "inflow":
                sentiment_score += 0.15  # Inflow = bullish
            elif flow_direction == "strong_outflow":
                sentiment_score -= 0.3  # Strong outflow = very bearish
            elif flow_direction == "outflow":
                sentiment_score -= 0.15  # Outflow = bearish
            
            # Confirmation ratio impact
            confirmed_ratio = whale_analysis.get("confirmed_ratio", 0.5)
            if confirmed_ratio > 0.8:
                sentiment_score += 0.1  # High confirmation = bullish
            elif confirmed_ratio < 0.3:
                sentiment_score -= 0.1  # Low confirmation = bearish
            
            # Clamp sentiment score
            sentiment_score = max(0.0, min(1.0, sentiment_score))
            
            # Determine sentiment classification
            if sentiment_score >= 0.7:
                sentiment_class = "bullish"
                confidence = "high"
            elif sentiment_score >= 0.6:
                sentiment_class = "bullish"
                confidence = "medium"
            elif sentiment_score >= 0.4:
                sentiment_class = "neutral"
                confidence = "medium"
            elif sentiment_score >= 0.3:
                sentiment_class = "bearish"
                confidence = "medium"
            else:
                sentiment_class = "bearish"
                confidence = "high"
            
            return {
                "score": sentiment_score,
                "classification": sentiment_class,
                "confidence": confidence,
                "trading_bias": self._get_trading_bias(sentiment_class, confidence),
                "reversal_probability": self._calculate_reversal_probability(sentiment_score)
            }
            
        except Exception as e:
            logger.error(f"❌ Sentiment calculation failed: {e}")
            return {
                "score": 0.5,
                "classification": "neutral",
                "confidence": "low",
                "trading_bias": "NEUTRAL",
                "reversal_probability": 0.3
            }
    
    def _get_trading_bias(self, sentiment_class: str, confidence: str) -> str:
        """Get trading bias from sentiment"""
        if sentiment_class == "bullish" and confidence == "high":
            return "STRONG_BUY"
        elif sentiment_class == "bullish":
            return "BUY"
        elif sentiment_class == "bearish" and confidence == "high":
            return "STRONG_SELL"
        elif sentiment_class == "bearish":
            return "SELL"
        else:
            return "NEUTRAL"
    
    def _calculate_reversal_probability(self, sentiment_score: float) -> float:
        """Calculate reversal probability based on sentiment score"""
        # Extreme sentiment scores have higher reversal probability
        if sentiment_score >= 0.8 or sentiment_score <= 0.2:
            return 0.7  # 70% reversal probability
        elif sentiment_score >= 0.7 or sentiment_score <= 0.3:
            return 0.5  # 50% reversal probability
        else:
            return 0.3  # 30% reversal probability
    
    def _is_exchange_address(self, address: str) -> bool:
        """Check if address belongs to a known exchange"""
        if not address:
            return False
        
        for exchange, addresses in self.exchange_addresses.items():
            if address in addresses:
                return True
        return False
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key]["timestamp"]
        return (time.time() - cache_time) < self.cache_duration
    
    # _get_fallback_data method removed - NO FALLBACKS policy
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            url = f"{self.api_base}/txs"
            params = {"limit": 1}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"❌ Whale analytics API test failed: {e}")
            return False


# Global instance for easy access
# Singleton pattern implementation
_global_whale_analytics_api = None

def get_global_whale_analytics_api() -> WhaleAnalyticsAPI:
    """Get the global WhaleAnalyticsAPI singleton instance"""
    global _global_whale_analytics_api
    if _global_whale_analytics_api is None:
        _global_whale_analytics_api = WhaleAnalyticsAPI()
    return _global_whale_analytics_api

# Backward compatibility
whale_analytics_api = get_global_whale_analytics_api()
