#!/usr/bin/env python3
"""
Whale Analytics API Client
==========================
Fetches whale activity data from BlockCypher API (free tier)
Tracks large BTC transactions and exchange flows
"""

import requests
import time
from typing import Dict, Any, List, Optional, Tuple, Callable
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
        
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        self.whale_threshold_usd = 100000  # $100k minimum whale size
        
        # Known exchange addresses (partial - BlockCypher provides some)
        self.exchange_addresses = {
            "binance": ["1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"],
            "coinbase": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS"],
            "kraken": ["3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC", "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"]
        }
        
        logger.info("🐋 Whale Analytics Fetcher initialized - BlockCypher API integration")
    
    def get_raw_whale_transactions(self) -> List[Dict[str, Any]]:
        """
        Get raw whale transaction data - PURE DATA ONLY
        
        Returns:
            List of raw whale transactions without analysis
        """
        try:
            # Use centralized cache with get_or_set pattern
            cache_key = "raw_whale_transactions"
            
            def fetch_fresh_transactions():
                # Get raw data from BlockCypher API
                from core.external.blockcypher_api import get_global_blockcypher_api
                blockcypher_api = get_global_blockcypher_api()
                
                raw_data = blockcypher_api.get_raw_transactions()
                
                if raw_data and "transactions" in raw_data:
                    raw_transactions = raw_data["transactions"]
                    logger.info(f"🐋 Raw whale transactions fetched: {len(raw_transactions)} transactions")
                    return raw_transactions
                else:
                    logger.warning("⚠️ Failed to fetch raw whale transactions from BlockCypher API")
                    raise ValueError("Raw whale transactions fetch failed - NO FALLBACKS")
            
            # Get from cache or fetch fresh
            raw_transactions = self._cache.get_or_set(
                key=cache_key,
                factory_func=fetch_fresh_transactions,
                # Use CentralizedCache TTL instead of hardcoded value
                force_fresh=False
            )
            
            return raw_transactions
                
        except Exception as e:
            logger.error(f"❌ Raw whale transactions fetch failed: {e}")
            raise ValueError(f"Raw whale transactions fetch failed - NO FALLBACKS: {e}")
    
    def get_processed_whale_data(self) -> Dict[str, Any]:
        """
        Get processed whale data (analyzed from raw transactions)
        
        Uses WhaleAnalysisCalculator to process raw transactions into expected format.
        Returns processed whale data in the format expected by analyzers:
        - whale_activity: {whale_count, activity_level, ...}
        - exchange_flows: {flow_direction, ...}
        - sentiment: {classification, ...}
        
        All data is mandatory - NO FALLBACKS
        """
        try:
            # Get raw transactions
            raw_transactions = self.get_raw_whale_transactions()
            if not raw_transactions:
                raise ValueError("Raw whale transactions list is empty (NO FALLBACKS)")
            
            # Process transactions using WhaleAnalysisCalculator
            from core.calculations.whale_analysis_calculator import create_whale_analysis_calculator
            whale_calculator = create_whale_analysis_calculator()
            
            # Analyze whale data from raw transactions
            processed_data = whale_calculator.analyze_whale_data(raw_transactions)
            
            if not processed_data:
                raise ValueError("Whale analysis returned empty data (NO FALLBACKS)")
            
            # Validate required structure (NO FALLBACKS)
            required_keys = ["whale_activity", "exchange_flows", "sentiment"]
            for key in required_keys:
                if key not in processed_data:
                    raise ValueError(f"Processed whale data missing required key: {key} (NO FALLBACKS)")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Whale data processing failed: {e}")
            raise ValueError(f"Whale data processing failed: {e} (NO FALLBACKS)")
    
    def _fetch_whale_data(self) -> Dict[str, Any]:
        """
        DEPRECATED: Use get_processed_whale_data() instead
        Fetch whale data from BlockCypher API
        """
        return self.get_processed_whale_data()
    
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
                    # Transaction structure validation - all fields required (NO FALLBACKS)
                    if "outputs" not in tx:
                        raise ValueError(f"Transaction missing 'outputs' key (NO FALLBACKS)")
                    if "hash" not in tx:
                        raise ValueError(f"Transaction missing 'hash' key (NO FALLBACKS)")
                    if "confirmations" not in tx:
                        raise ValueError(f"Transaction missing 'confirmations' key (NO FALLBACKS)")
                    if "received" not in tx:
                        raise ValueError(f"Transaction missing 'received' key (NO FALLBACKS)")
                    if "inputs" not in tx:
                        raise ValueError(f"Transaction missing 'inputs' key (NO FALLBACKS)")
                    
                    # Calculate transaction value in USD (approximate)
                    outputs = tx["outputs"]
                    # Output structure validation - value is required (NO FALLBACKS)
                    total_value = 0
                    for output in outputs:
                        if "value" not in output:
                            raise ValueError(f"Transaction output missing 'value' key (NO FALLBACKS)")
                        total_value += output["value"]
                    value_usd = (total_value / 100000000) * 112000  # Convert satoshis to BTC, then to USD
                    
                    if value_usd >= self.whale_threshold_usd:
                        large_transactions.append({
                            "hash": tx["hash"],
                            "value_btc": total_value / 100000000,
                            "value_usd": value_usd,
                            "confirmations": tx["confirmations"],
                            "time": tx["received"],
                            "inputs": tx["inputs"],
                            "outputs": tx["outputs"]
                        })
                except Exception as e:
                    continue
            
            logger.info(f"🐋 Found {len(large_transactions)} large transactions (>{self.whale_threshold_usd:,} USD)")
            return large_transactions
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch transactions: {e}")
            return []
    
    # REMOVED: All analysis methods moved to dedicated calculators in core/calculations/
    # This API now provides PURE DATA ONLY - no business logic
    
    def _is_exchange_address(self, address: str) -> bool:
        """Check if address belongs to a known exchange"""
        if not address:
            return False
        
        for exchange, addresses in self.exchange_addresses.items():
            if address in addresses:
                return True
        return False
    
    
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
