#!/usr/bin/env python3
"""
Whale Analysis Calculator
=========================
Processes raw whale transaction data to provide whale analytics
"""

import time
from typing import Dict, Any, List, Tuple
from loguru import logger


class WhaleAnalysisCalculator:
    """
    Calculates whale analytics from raw transaction data
    
    Features:
    - Whale activity detection (>$100k transactions)
    - Exchange flow analysis
    - Whale sentiment calculation
    - Volume and count metrics
    """
    
    def __init__(self):
        self.whale_threshold_usd = 100000  # $100k minimum whale size
        self.analysis_window_hours = 6  # Analyze last 6 hours
        
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        # Known exchange addresses
        self.exchange_addresses = {
            "binance": ["1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"],
            "coinbase": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS"],
            "kraken": ["3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC", "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"]
        }
        
        logger.info("🐋 Whale Analysis Calculator initialized")
    
    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest whale analysis - calculate fresh data instead of relying on cache
        
        Returns:
            Dict containing latest whale analysis data
        """
        try:
            # Get fresh whale transaction data
            from core.external.whale_analytics_api import get_global_whale_analytics_api
            whale_api = get_global_whale_analytics_api()
            
            if not whale_api:
                logger.warning("⚠️ Whale Analytics API not available")
                raise ValueError("Whale Analytics API not available - NO FALLBACKS")
            
            # Fetch raw whale transactions
            raw_transactions = whale_api.get_raw_whale_transactions()
            
            if not raw_transactions:
                logger.debug("🐋 No whale transactions available")
                raise ValueError("No whale transactions available - NO FALLBACKS")
            
            # Analyze the whale data
            analysis_result = self.analyze_whale_data(raw_transactions)
            
            # Cache the result
            # Use CentralizedCache TTL instead of hardcoded value
            self._cache.set("whale_analysis", analysis_result)
            
            logger.info(f"🐋 Fresh whale analysis completed: {analysis_result['whale_activity']['whale_count']} whales")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest whale analysis: {e}")
            # NO FALLBACKS - Raise error instead of returning neutral analysis
            raise ValueError(f"Whale analysis failed - NO FALLBACKS: {e}")
    
    # _create_neutral_whale_analysis method removed - NO FALLBACKS policy
    # If whale analysis fails, it should raise an error instead of returning neutral values
    
    def _create_empty_whale_activity(self) -> Dict[str, Any]:
        """Create empty whale activity response - follows DRY"""
        return {
            "whale_count": 0,
            "activity_level": "low",
            "total_volume_usd": 0,
            "average_transaction_size": 0,
            "largest_transaction": 0
        }
    
    def _create_empty_exchange_flows(self) -> Dict[str, Any]:
        """Create empty exchange flows response - follows DRY"""
        return {
            "flow_direction": "neutral",
            "net_flow": 0,
            "inflow_volume": 0,
            "outflow_volume": 0,
            "exchange_transactions": 0
        }
    
    def _create_neutral_sentiment(self) -> Dict[str, Any]:
        """Create neutral sentiment response - follows DRY"""
        return {
            "classification": "neutral",
            "confidence": "low",
            "sentiment_score": 0,
            "factors": {}
        }
    
    def analyze_whale_data(self, raw_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze raw whale transaction data
        
        Args:
            raw_transactions: List of raw transaction data
            
        Returns:
            Dict containing whale activity, exchange flows, and sentiment
        """
        try:
            # Use centralized cache with get_or_set pattern
            cache_key = f"whale_analysis_{len(raw_transactions)}"
            
            def calculate_fresh_whale_analysis():
                # Filter for whale transactions (last 6 hours)
                whale_transactions = self._filter_whale_transactions(raw_transactions)
                
                # Analyze whale activity
                whale_activity = self._analyze_whale_activity(whale_transactions)
                
                # Analyze exchange flows
                exchange_flows = self._analyze_exchange_flows(whale_transactions)
                
                # Calculate sentiment
                sentiment = self._calculate_whale_sentiment(whale_activity, exchange_flows)
                
                result = {
                    "whale_activity": whale_activity,
                    "exchange_flows": exchange_flows,
                    "sentiment": sentiment,
                    "timestamp": time.time(),
                    "data_source": "whale_analysis_calculator"
                }
                
                logger.info(f"🐋 Whale analysis completed: {whale_activity.get('whale_count', 0)} whales, {sentiment.get('classification', 'neutral')} sentiment")
                return result
            
            # Get from cache or calculate fresh
            result = self._cache.get_or_set(
                key=cache_key,
                factory_func=calculate_fresh_whale_analysis,
                # Use CentralizedCache TTL instead of hardcoded value
                force_fresh=False
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Whale analysis failed: {e}")
            raise ValueError(f"Whale analysis failed: {e}")
    
    def _filter_whale_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter transactions for whale activity (last 6 hours, >$100k)"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (self.analysis_window_hours * 3600)
            
            whale_transactions = []
            
            for tx in transactions:
                try:
                    # Check if transaction is recent enough
                    tx_time = self._parse_transaction_time(tx.get("received", ""))
                    if tx_time < cutoff_time:
                        continue
                    
                    # Calculate transaction value
                    total_value = sum(output.get("value", 0) for output in tx.get("outputs", []))
                    value_btc = total_value / 100000000  # Convert satoshis to BTC
                    
                    # Approximate USD value (using current BTC price ~$110k)
                    value_usd = value_btc * 110000
                    
                    if value_usd >= self.whale_threshold_usd:
                        whale_transactions.append({
                            "hash": tx.get("hash"),
                            "value_btc": value_btc,
                            "value_usd": value_usd,
                            "time": tx_time,
                            "inputs": tx.get("inputs", []),
                            "outputs": tx.get("outputs", []),
                            "addresses": tx.get("addresses", [])
                        })
                        
                except Exception as e:
                    continue
            
            logger.info(f"🐋 Filtered {len(whale_transactions)} whale transactions from {len(transactions)} total")
            return whale_transactions
            
        except Exception as e:
            logger.error(f"❌ Failed to filter whale transactions: {e}")
            return []
    
    def _analyze_whale_activity(self, whale_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze whale activity patterns"""
        try:
            if not whale_transactions:
                return self._create_empty_whale_activity()
            
            # Count whales and calculate volume
            whale_count = len(whale_transactions)
            total_volume_usd = sum(tx["value_usd"] for tx in whale_transactions)
            average_size = total_volume_usd / whale_count if whale_count > 0 else 0
            largest_transaction = max(tx["value_usd"] for tx in whale_transactions)
            
            # Determine activity level
            if whale_count >= 10 or total_volume_usd >= 10000000:  # 10+ whales or $10M+ volume
                activity_level = "very_high"
            elif whale_count >= 5 or total_volume_usd >= 5000000:  # 5+ whales or $5M+ volume
                activity_level = "high"
            elif whale_count >= 2 or total_volume_usd >= 1000000:  # 2+ whales or $1M+ volume
                activity_level = "medium"
            else:
                activity_level = "low"
            
            return {
                "whale_count": whale_count,
                "activity_level": activity_level,
                "total_volume_usd": total_volume_usd,
                "average_transaction_size": average_size,
                "largest_transaction": largest_transaction
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze whale activity: {e}")
            return self._create_empty_whale_activity()
    
    def _analyze_exchange_flows(self, whale_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze exchange flows from whale transactions"""
        try:
            if not whale_transactions:
                return self._create_empty_exchange_flows()
            
            inflow_volume = 0
            outflow_volume = 0
            exchange_transactions = 0
            
            for tx in whale_transactions:
                has_exchange_involvement = False
                tx_inflow = 0
                tx_outflow = 0
                
                # Check inputs for exchange addresses
                for input_tx in tx.get("inputs", []):
                    addresses = input_tx.get("addresses", [])
                    if addresses is not None:  # Check for None
                        for address in addresses:
                            if self._is_exchange_address(address):
                                has_exchange_involvement = True
                                tx_outflow += input_tx.get("output_value", 0) / 100000000  # Convert to BTC
                
                # Check outputs for exchange addresses
                for output in tx.get("outputs", []):
                    addresses = output.get("addresses", [])
                    if addresses is not None:  # Check for None
                        for address in addresses:
                            if self._is_exchange_address(address):
                                has_exchange_involvement = True
                                tx_inflow += output.get("value", 0) / 100000000  # Convert to BTC
                
                if has_exchange_involvement:
                    exchange_transactions += 1
                    inflow_volume += tx_inflow
                    outflow_volume += tx_outflow
            
            net_flow = inflow_volume - outflow_volume
            
            # Determine flow direction
            if net_flow > 100:  # >100 BTC net inflow
                flow_direction = "strong_inflow"
            elif net_flow > 10:  # >10 BTC net inflow
                flow_direction = "inflow"
            elif net_flow < -100:  # >100 BTC net outflow
                flow_direction = "strong_outflow"
            elif net_flow < -10:  # >10 BTC net outflow
                flow_direction = "outflow"
            else:
                flow_direction = "neutral"
            
            return {
                "flow_direction": flow_direction,
                "net_flow": net_flow,
                "inflow_volume": inflow_volume,
                "outflow_volume": outflow_volume,
                "exchange_transactions": exchange_transactions
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze exchange flows: {e}")
            return self._create_empty_exchange_flows()
    
    def _calculate_whale_sentiment(self, whale_activity: Dict[str, Any], exchange_flows: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate whale sentiment based on activity and flows"""
        try:
            activity_level = whale_activity.get("activity_level", "low")
            flow_direction = exchange_flows.get("flow_direction", "neutral")
            whale_count = whale_activity.get("whale_count", 0)
            
            # Base sentiment scoring
            sentiment_score = 0
            
            # Activity-based sentiment
            if activity_level == "very_high":
                sentiment_score += 2
            elif activity_level == "high":
                sentiment_score += 1
            elif activity_level == "medium":
                sentiment_score += 0
            else:  # low
                sentiment_score -= 1
            
            # Flow-based sentiment
            if flow_direction == "strong_inflow":
                sentiment_score += 3
            elif flow_direction == "inflow":
                sentiment_score += 1
            elif flow_direction == "strong_outflow":
                sentiment_score -= 3
            elif flow_direction == "outflow":
                sentiment_score -= 1
            
            # Volume-based sentiment (high volume = more significant)
            total_volume = whale_activity.get("total_volume_usd", 0)
            if total_volume > 50000000:  # >$50M
                sentiment_score += 2
            elif total_volume > 10000000:  # >$10M
                sentiment_score += 1
            elif total_volume < 1000000:  # <$1M
                sentiment_score -= 1
            
            # Determine sentiment classification
            if sentiment_score >= 3:
                classification = "bullish"
                confidence = "high" if whale_count >= 5 else "medium"
            elif sentiment_score >= 1:
                classification = "bullish"
                confidence = "low"
            elif sentiment_score <= -3:
                classification = "bearish"
                confidence = "high" if whale_count >= 5 else "medium"
            elif sentiment_score <= -1:
                classification = "bearish"
                confidence = "low"
            else:
                classification = "neutral"
                confidence = "low"
            
            return {
                "classification": classification,
                "confidence": confidence,
                "sentiment_score": sentiment_score,
                "factors": {
                    "activity_level": activity_level,
                    "flow_direction": flow_direction,
                    "whale_count": whale_count,
                    "total_volume": total_volume
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate whale sentiment: {e}")
            return self._create_neutral_sentiment()
    
    def _is_exchange_address(self, address: str) -> bool:
        """Check if address belongs to a known exchange"""
        if not address:
            return False
        
        for exchange, addresses in self.exchange_addresses.items():
            if address in addresses:
                return True
        return False
    
    def _parse_transaction_time(self, time_str: str) -> float:
        """Parse transaction time string to timestamp"""
        try:
            if not time_str:
                return 0
            
            # Handle ISO format timestamps
            if "T" in time_str:
                from datetime import datetime
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                return dt.timestamp()
            
            # Handle Unix timestamp
            return float(time_str)
            
        except Exception:
            return 0
    


# Factory function for dependency injection
def create_whale_analysis_calculator() -> WhaleAnalysisCalculator:
    """
    Factory function to create WhaleAnalysisCalculator with dependency injection
    
    Returns:
        Configured WhaleAnalysisCalculator instance
    """
    return WhaleAnalysisCalculator()

# Deprecated singleton functions removed - use create_whale_analysis_calculator() instead
