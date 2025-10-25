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
        
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
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
        return self._cache.get(key)

    def _cache_data(self, key: str, data: Dict[str, Any]):
        """Cache data with current timestamp"""
        self._cache.set(key, data, ttl=300)  # 5 minutes cache

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

    def get_raw_transactions(self) -> List[Dict[str, Any]]:
        """
        Get raw transaction data from BlockCypher API - PURE DATA ONLY
        
        Returns:
            List of raw transactions without filtering or analysis
        """
        try:
            cache_key = "raw_transactions"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Get recent transactions (PURE DATA)
            transactions = self.get_recent_transactions(limit=100)
            
            # Return raw transactions - NO BUSINESS LOGIC
            result = {
                "transactions": transactions,
                "count": len(transactions),
                "timestamp": time.time(),
                "data_source": "blockcypher_api"
            }
            
            self._cache_data(cache_key, result)
            logger.info(f"✅ Raw transactions fetched: {len(transactions)} transactions")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get whale transactions: {e}")
            raise ValueError(f"Whale transactions fetch failed: {e}")

    # REMOVED: All analysis methods moved to dedicated calculators in core/calculations/
    # This API now provides PURE DATA ONLY - no business logic

    def get_whale_analytics(self) -> Dict[str, Any]:
        """
        Get raw whale transaction data using BlockCypher API - PURE DATA ONLY
        
        Returns:
            Dictionary with raw whale transaction data
        """
        try:
            # Get raw transactions (PURE DATA)
            raw_data = self.get_raw_transactions()
            
            if raw_data and "transactions" in raw_data:
                return {
                    "transactions": raw_data["transactions"],
                    "count": raw_data["count"],
                    "timestamp": raw_data["timestamp"],
                    "data_source": "blockcypher_api"
                }
            else:
                raise ValueError("No raw transaction data available from BlockCypher API")
                
        except Exception as e:
            logger.error(f"❌ Failed to get raw whale data: {e}")
            raise ValueError(f"Raw whale data fetch failed: {e}")

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
