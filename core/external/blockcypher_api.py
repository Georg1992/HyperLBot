#!/usr/bin/env python3
"""
BlockCypher API Client
======================
Fetches real whale transaction data from BlockCypher API (COMPLETELY FREE)
Provides actual large transaction monitoring for Bitcoin - NO API KEY REQUIRED
"""

import requests
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timedelta

# Singleton pattern implementation
_global_blockcypher_api = None

def get_global_blockcypher_api() -> 'BlockCypherAPI':
    """Get the global BlockCypherAPI singleton instance"""
    global _global_blockcypher_api
    if _global_blockcypher_api is None:
        _global_blockcypher_api = BlockCypherAPI()
    return _global_blockcypher_api

class BlockCypherAPI:
    """
    BlockCypher API client for real whale transaction monitoring
    COMPLETELY FREE - No API key required, no registration needed
    """

    def __init__(self):
        # BlockCypher API configuration
        self.api_base_url = "https://api.blockcypher.com/v1/btc/main"
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_duration = 300  # 5 minutes cache
        self.rate_limit_delay = 1  # 1 second between requests (generous rate limit)
        
        # Whale transaction thresholds (BTC)
        self.whale_thresholds = {
            "small_whale": 10,      # 10 BTC
            "medium_whale": 100,    # 100 BTC
            "large_whale": 1000,    # 1000 BTC
            "mega_whale": 5000      # 5000 BTC
        }
        
        logger.info("🐋 BlockCypher API Client initialized - COMPLETELY FREE whale transaction monitoring")

    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache if valid"""
        if key in self.cache and (time.time() - self.cache_timestamps.get(key, 0) < self.cache_duration):
            return self.cache[key]
        return None

    def _cache_data(self, key: str, data: Dict[str, Any]):
        """Cache data with current timestamp"""
        self.cache[key] = data
        self.cache_timestamps[key] = time.time()

    def _rate_limit(self):
        """Enforce rate limiting"""
        time.sleep(self.rate_limit_delay)

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make request to BlockCypher API (no authentication required)"""
        self._rate_limit()
        
        url = f"{self.api_base_url}/{endpoint}"
        headers = {
            "User-Agent": "HyperLBot/1.0"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ BlockCypher API request failed: {e}")
            return None

    def get_recent_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent Bitcoin transactions from BlockCypher
        
        Args:
            limit: Maximum number of transactions to return (default: 50)
            
        Returns:
            List of recent transactions
        """
        try:
            cache_key = f"recent_transactions_{limit}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            logger.info(f"🐋 Fetching {limit} recent transactions from BlockCypher API")
            response = self._make_request("txs", {"limit": limit})
            
            if response:
                self._cache_data(cache_key, response)
                logger.info(f"✅ BlockCypher data fetched: {len(response)} transactions")
                return response
            else:
                raise ValueError("No transaction data available from BlockCypher API")
                
        except Exception as e:
            logger.error(f"❌ Failed to get recent transactions: {e}")
            raise ValueError(f"BlockCypher API fetch failed: {e}")

    def get_whale_transactions(self, min_btc: float = 10.0) -> Dict[str, Any]:
        """
        Get whale transactions from BlockCypher API
        
        Args:
            min_btc: Minimum transaction value in BTC (default: 10 BTC)
            
        Returns:
            Dictionary with whale transaction data
        """
        try:
            cache_key = f"whale_transactions_{min_btc}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Get recent transactions
            transactions = self.get_recent_transactions(limit=100)
            
            # Filter for whale transactions
            whale_transactions = []
            min_satoshis = int(min_btc * 100000000)  # Convert BTC to satoshis
            
            for tx in transactions:
                # Calculate total output value
                total_value = sum(output.get('value', 0) for output in tx.get('outputs', []))
                
                if total_value >= min_satoshis:
                    whale_transactions.append({
                        'hash': tx.get('hash', ''),
                        'value_btc': total_value / 100000000,
                        'value_satoshis': total_value,
                        'confirmations': tx.get('confirmations', 0),
                        'received': tx.get('received', ''),
                        'inputs': len(tx.get('inputs', [])),
                        'outputs': len(tx.get('outputs', []))
                    })
            
            # Analyze whale activity
            whale_analysis = self._analyze_whale_activity(whale_transactions)
            
            result = {
                "whale_transactions": whale_transactions,
                "whale_analysis": whale_analysis,
                "count": len(whale_transactions),
                "min_btc": min_btc,
                "timestamp": time.time(),
                "data_source": "blockcypher_api"
            }
            
            self._cache_data(cache_key, result)
            logger.info(f"✅ Whale transactions fetched: {len(whale_transactions)} whales, {whale_analysis['activity_level']} activity")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get whale transactions: {e}")
            raise ValueError(f"Whale transactions fetch failed: {e}")

    def _analyze_whale_activity(self, whale_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze whale activity from transaction data"""
        if not whale_transactions:
            return {
                "activity_level": "NONE",
                "whale_count": 0,
                "total_volume_btc": 0,
                "largest_transaction_btc": 0,
                "whale_breakdown": {"small": 0, "medium": 0, "large": 0, "mega": 0},
                "sentiment": "NEUTRAL"
            }
        
        # Calculate metrics
        total_volume = sum(tx['value_btc'] for tx in whale_transactions)
        largest_tx = max(whale_transactions, key=lambda x: x['value_btc'])
        largest_amount = largest_tx['value_btc']
        
        # Count whales by size
        whale_counts = {
            "small": 0,
            "medium": 0,
            "large": 0,
            "mega": 0
        }
        
        for tx in whale_transactions:
            amount_btc = tx['value_btc']
            if amount_btc >= self.whale_thresholds["mega_whale"]:
                whale_counts["mega"] += 1
            elif amount_btc >= self.whale_thresholds["large_whale"]:
                whale_counts["large"] += 1
            elif amount_btc >= self.whale_thresholds["medium_whale"]:
                whale_counts["medium"] += 1
            elif amount_btc >= self.whale_thresholds["small_whale"]:
                whale_counts["small"] += 1
        
        total_whales = sum(whale_counts.values())
        
        # Determine activity level
        if total_whales >= 10 or largest_amount >= 5000:
            activity_level = "EXTREME"
        elif total_whales >= 5 or largest_amount >= 1000:
            activity_level = "HIGH"
        elif total_whales >= 2 or largest_amount >= 100:
            activity_level = "MODERATE"
        elif total_whales >= 1:
            activity_level = "LOW"
        else:
            activity_level = "NONE"
        
        # Determine sentiment based on transaction patterns
        if total_volume > 1000:  # > 1000 BTC total volume
            sentiment = "BULLISH"
        elif total_volume > 100:  # > 100 BTC total volume
            sentiment = "NEUTRAL"
        else:
            sentiment = "BEARISH"
        
        return {
            "activity_level": activity_level,
            "whale_count": total_whales,
            "whale_breakdown": whale_counts,
            "total_volume_btc": total_volume,
            "largest_transaction_btc": largest_amount,
            "sentiment": sentiment
        }

    def get_whale_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive whale analytics using BlockCypher API
        
        Returns:
            Dictionary with whale activity analysis
        """
        try:
            # Get whale transactions (10+ BTC threshold)
            whale_data = self.get_whale_transactions(min_btc=10.0)
            
            if whale_data:
                return {
                    "whale_activity": whale_data["whale_analysis"],
                    "recent_transactions": whale_data["whale_transactions"][:5],  # Last 5 transactions
                    "timestamp": time.time(),
                    "data_source": "blockcypher_api"
                }
            else:
                raise ValueError("No whale data available from BlockCypher API")
                
        except Exception as e:
            logger.error(f"❌ Failed to get whale analytics: {e}")
            raise ValueError(f"Whale analytics fetch failed: {e}")

    def test_connection(self) -> bool:
        """Test BlockCypher API connection"""
        try:
            logger.info("🔍 Testing BlockCypher API connection...")
            response = self._make_request("")
            
            if response and "name" in response:
                logger.info("✅ BlockCypher API connection successful")
                return True
            else:
                logger.error("❌ BlockCypher API connection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ BlockCypher API connection test failed: {e}")
            return False

# Backward compatibility
blockcypher_api = get_global_blockcypher_api()
