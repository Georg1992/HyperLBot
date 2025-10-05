#!/usr/bin/env python3
"""
On-Chain Data Analyzer Module
Analyzes blockchain data for exchange flows, active addresses, and mining metrics
"""

import time
# import requests  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger

# Singleton pattern implementation
_global_onchain_data_analyzer = None

def get_global_onchain_data_analyzer() -> 'OnChainDataAnalyzer':
    """Get the global OnChainDataAnalyzer singleton instance"""
    global _global_onchain_data_analyzer
    if _global_onchain_data_analyzer is None:
        _global_onchain_data_analyzer = OnChainDataAnalyzer()
    return _global_onchain_data_analyzer

class OnChainDataAnalyzer:
    """Analyzes on-chain data for blockchain insights"""
    
    def __init__(self):
        # Cache for on-chain data to avoid excessive API calls
        self._data_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 600  # 10 minutes cache for on-chain data (slower changing)
        
        # On-chain metrics history for trend analysis
        self._metrics_history = []
        self._max_history = 30  # Keep last 30 readings
        
        logger.info("📊 On-Chain Data Analyzer initialized")
    
    def analyze_onchain_data(self, btc_price: float) -> Dict[str, Any]:
        """
        Analyze on-chain data for blockchain insights
        
        Args:
            btc_price: Current Bitcoin price for context
            
        Returns:
            Dictionary with on-chain data analysis
        """
        try:
            # Get on-chain metrics
            exchange_flows = self._get_exchange_flows()
            active_addresses = self._get_active_addresses()
            mining_metrics = self._get_mining_metrics()
            network_metrics = self._get_network_metrics()
            
            # Calculate analysis
            analysis = {
                "exchange_flows": self._analyze_exchange_flows(exchange_flows, btc_price),
                "active_addresses": self._analyze_active_addresses(active_addresses),
                "mining_metrics": self._analyze_mining_metrics(mining_metrics),
                "network_health": self._analyze_network_health(network_metrics),
                "whale_activity": self._analyze_whale_activity(exchange_flows),
                "onchain_sentiment": self._determine_onchain_sentiment(exchange_flows, active_addresses, mining_metrics),
                "timestamp": time.time(),
                "data_source": "onchain_apis"
            }
            
            # Update metrics history
            self._update_metrics_history(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ On-chain data analysis failed: {e}")
            raise Exception(f"On-chain data analysis failed: {e}")
    
    def _get_exchange_flows(self) -> Dict[str, Any]:
        """Get exchange inflow/outflow data"""
        try:
            cache_key = "exchange_flows"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Mock exchange flow data (in production, use Glassnode, CryptoQuant, or similar)
            exchange_flows = {
                "inflows": {
                    "total_btc": 1250.5,  # BTC flowing into exchanges
                    "total_usd": 1250.5 * 45000,  # USD value
                    "change_24h": -150.2,  # Change from yesterday
                    "change_24h_pct": -10.7,  # Percentage change
                    "top_exchanges": [
                        {"name": "Binance", "btc": 450.2, "pct": 36.0},
                        {"name": "Coinbase", "btc": 320.1, "pct": 25.6},
                        {"name": "Kraken", "btc": 180.3, "pct": 14.4}
                    ]
                },
                "outflows": {
                    "total_btc": 1180.3,  # BTC flowing out of exchanges
                    "total_usd": 1180.3 * 45000,  # USD value
                    "change_24h": 200.5,  # Change from yesterday
                    "change_24h_pct": 20.4,  # Percentage change
                    "top_exchanges": [
                        {"name": "Binance", "btc": 380.1, "pct": 32.2},
                        {"name": "Coinbase", "btc": 290.5, "pct": 24.6},
                        {"name": "Kraken", "btc": 165.2, "pct": 14.0}
                    ]
                },
                "net_flow": {
                    "btc": 70.2,  # Net flow (inflows - outflows)
                    "usd": 70.2 * 45000,
                    "direction": "INFLOW",  # More flowing in than out
                    "trend": "INCREASING"
                },
                "timestamp": time.time(),
                "data_source": "mock_exchange_flows"
            }
            
            self._cache_data(cache_key, exchange_flows)
            return exchange_flows
            
        except Exception as e:
            logger.error(f"❌ Failed to get exchange flows: {e}")
            return {"error": str(e), "inflows": {}, "outflows": {}, "net_flow": {}}
    
    def _get_active_addresses(self) -> Dict[str, Any]:
        """Get active addresses data"""
        try:
            cache_key = "active_addresses"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Mock active addresses data
            active_addresses = {
                "daily_active": {
                    "count": 875000,  # Daily active addresses
                    "change_24h": 12500,  # Change from yesterday
                    "change_24h_pct": 1.45,  # Percentage change
                    "trend": "INCREASING"
                },
                "weekly_active": {
                    "count": 2100000,  # Weekly active addresses
                    "change_7d": 45000,  # Change from last week
                    "change_7d_pct": 2.19,  # Percentage change
                    "trend": "INCREASING"
                },
                "monthly_active": {
                    "count": 4500000,  # Monthly active addresses
                    "change_30d": 180000,  # Change from last month
                    "change_30d_pct": 4.17,  # Percentage change
                    "trend": "INCREASING"
                },
                "new_addresses": {
                    "daily_new": 125000,  # New addresses created today
                    "change_24h": 5000,  # Change from yesterday
                    "change_24h_pct": 4.17,  # Percentage change
                    "trend": "INCREASING"
                },
                "timestamp": time.time(),
                "data_source": "mock_active_addresses"
            }
            
            self._cache_data(cache_key, active_addresses)
            return active_addresses
            
        except Exception as e:
            logger.error(f"❌ Failed to get active addresses: {e}")
            return {"error": str(e), "daily_active": {}, "weekly_active": {}, "monthly_active": {}}
    
    def _get_mining_metrics(self) -> Dict[str, Any]:
        """Get mining metrics data"""
        try:
            cache_key = "mining_metrics"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Mock mining metrics data
            mining_metrics = {
                "hash_rate": {
                    "current_th_s": 450.5,  # Current hash rate in TH/s
                    "change_24h": 12.3,  # Change from yesterday
                    "change_24h_pct": 2.81,  # Percentage change
                    "trend": "INCREASING",
                    "all_time_high": 500.2
                },
                "mining_difficulty": {
                    "current": 67.2,  # Current difficulty
                    "change_24h": 1.8,  # Change from yesterday
                    "change_24h_pct": 2.75,  # Percentage change
                    "trend": "INCREASING",
                    "next_adjustment": "2024-01-15T12:00:00Z"
                },
                "mining_revenue": {
                    "daily_usd": 45000000,  # Daily mining revenue in USD
                    "change_24h": 2500000,  # Change from yesterday
                    "change_24h_pct": 5.88,  # Percentage change
                    "trend": "INCREASING"
                },
                "miner_flows": {
                    "to_exchanges": 850.2,  # BTC sent to exchanges by miners
                    "change_24h": -120.5,  # Change from yesterday
                    "change_24h_pct": -12.4,  # Percentage change
                    "trend": "DECREASING"
                },
                "timestamp": time.time(),
                "data_source": "mock_mining_metrics"
            }
            
            self._cache_data(cache_key, mining_metrics)
            return mining_metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get mining metrics: {e}")
            return {"error": str(e), "hash_rate": {}, "mining_difficulty": {}, "mining_revenue": {}}
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """Get network health metrics"""
        try:
            cache_key = "network_metrics"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Mock network metrics data
            network_metrics = {
                "transaction_count": {
                    "daily": 285000,  # Daily transaction count
                    "change_24h": 8500,  # Change from yesterday
                    "change_24h_pct": 3.08,  # Percentage change
                    "trend": "INCREASING"
                },
                "transaction_volume": {
                    "daily_btc": 125000,  # Daily transaction volume in BTC
                    "daily_usd": 125000 * 45000,  # Daily transaction volume in USD
                    "change_24h": 8500,  # Change from yesterday
                    "change_24h_pct": 7.3,  # Percentage change
                    "trend": "INCREASING"
                },
                "average_transaction_fee": {
                    "current_sats": 15.2,  # Current average fee in satoshis
                    "current_usd": 0.68,  # Current average fee in USD
                    "change_24h": -2.1,  # Change from yesterday
                    "change_24h_pct": -12.1,  # Percentage change
                    "trend": "DECREASING"
                },
                "mempool_size": {
                    "current_mb": 45.2,  # Current mempool size in MB
                    "change_24h": -5.8,  # Change from yesterday
                    "change_24h_pct": -11.4,  # Percentage change
                    "trend": "DECREASING"
                },
                "timestamp": time.time(),
                "data_source": "mock_network_metrics"
            }
            
            self._cache_data(cache_key, network_metrics)
            return network_metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get network metrics: {e}")
            return {"error": str(e), "transaction_count": {}, "transaction_volume": {}, "average_transaction_fee": {}}
    
    def _analyze_exchange_flows(self, flows_data: Dict[str, Any], btc_price: float) -> Dict[str, Any]:
        """Analyze exchange flow patterns"""
        try:
            if not flows_data or "error" in flows_data:
                return {"analysis": "NO_DATA", "sentiment": "UNKNOWN", "impact": "UNKNOWN"}
            
            net_flow = flows_data.get("net_flow", {})
            net_btc = net_flow.get("btc", 0)
            direction = net_flow.get("direction", "UNKNOWN")
            
            # Analyze flow sentiment
            if direction == "INFLOW" and net_btc > 100:
                sentiment = "BEARISH"
                impact = "HIGH"
                interpretation = "Large inflows to exchanges - selling pressure expected"
            elif direction == "INFLOW" and net_btc > 50:
                sentiment = "SLIGHTLY_BEARISH"
                impact = "MEDIUM"
                interpretation = "Moderate inflows to exchanges - some selling pressure"
            elif direction == "OUTFLOW" and abs(net_btc) > 100:
                sentiment = "BULLISH"
                impact = "HIGH"
                interpretation = "Large outflows from exchanges - accumulation phase"
            elif direction == "OUTFLOW" and abs(net_btc) > 50:
                sentiment = "SLIGHTLY_BULLISH"
                impact = "MEDIUM"
                interpretation = "Moderate outflows from exchanges - some accumulation"
            else:
                sentiment = "NEUTRAL"
                impact = "LOW"
                interpretation = "Balanced exchange flows - neutral impact"
            
            return {
                "analysis": f"{sentiment}_{impact}",
                "sentiment": sentiment,
                "impact": impact,
                "interpretation": interpretation,
                "net_flow_btc": net_btc,
                "net_flow_usd": net_btc * btc_price,
                "direction": direction,
                "top_exchange": flows_data.get("inflows", {}).get("top_exchanges", [{}])[0].get("name", "Unknown")
            }
            
        except Exception as e:
            logger.error(f"❌ Exchange flow analysis failed: {e}")
            return {"analysis": "ERROR", "sentiment": "UNKNOWN", "impact": "UNKNOWN"}
    
    def _analyze_active_addresses(self, addresses_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze active addresses patterns"""
        try:
            if not addresses_data or "error" in addresses_data:
                return {"analysis": "NO_DATA", "trend": "UNKNOWN", "health": "UNKNOWN"}
            
            daily_active = addresses_data.get("daily_active", {})
            weekly_active = addresses_data.get("weekly_active", {})
            new_addresses = addresses_data.get("new_addresses", {})
            
            daily_count = daily_active.get("count", 0)
            daily_change = daily_active.get("change_24h_pct", 0)
            weekly_change = weekly_active.get("change_7d_pct", 0)
            new_change = new_addresses.get("change_24h_pct", 0)
            
            # Analyze network activity health
            if daily_change > 5 and weekly_change > 3 and new_change > 5:
                health = "EXCELLENT"
                trend = "STRONG_GROWTH"
                interpretation = "Strong growth across all address metrics - healthy network"
            elif daily_change > 2 and weekly_change > 1:
                health = "GOOD"
                trend = "GROWING"
                interpretation = "Positive growth in network activity"
            elif daily_change > 0 and weekly_change > 0:
                health = "FAIR"
                trend = "SLOW_GROWTH"
                interpretation = "Modest growth in network activity"
            elif daily_change < -5 or weekly_change < -3:
                health = "POOR"
                trend = "DECLINING"
                interpretation = "Declining network activity - concerning"
            else:
                health = "NEUTRAL"
                trend = "STABLE"
                interpretation = "Stable network activity"
            
            return {
                "analysis": f"{health}_{trend}",
                "health": health,
                "trend": trend,
                "interpretation": interpretation,
                "daily_active": daily_count,
                "daily_change_pct": daily_change,
                "weekly_change_pct": weekly_change,
                "new_addresses_change_pct": new_change
            }
            
        except Exception as e:
            logger.error(f"❌ Active addresses analysis failed: {e}")
            return {"analysis": "ERROR", "trend": "UNKNOWN", "health": "UNKNOWN"}
    
    def _analyze_mining_metrics(self, mining_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mining metrics"""
        try:
            if not mining_data or "error" in mining_data:
                return {"analysis": "NO_DATA", "security": "UNKNOWN", "trend": "UNKNOWN"}
            
            hash_rate = mining_data.get("hash_rate", {})
            difficulty = mining_data.get("mining_difficulty", {})
            miner_flows = mining_data.get("miner_flows", {})
            
            hash_rate_change = hash_rate.get("change_24h_pct", 0)
            difficulty_change = difficulty.get("change_24h_pct", 0)
            miner_flows_change = miner_flows.get("change_24h_pct", 0)
            
            # Analyze network security
            if hash_rate_change > 5 and difficulty_change > 2:
                security = "VERY_STRONG"
                trend = "INCREASING"
                interpretation = "Strong hash rate growth - excellent network security"
            elif hash_rate_change > 2 and difficulty_change > 1:
                security = "STRONG"
                trend = "GROWING"
                interpretation = "Good hash rate growth - strong network security"
            elif hash_rate_change > 0:
                security = "ADEQUATE"
                trend = "STABLE"
                interpretation = "Stable hash rate - adequate network security"
            elif hash_rate_change < -5:
                security = "WEAK"
                trend = "DECLINING"
                interpretation = "Declining hash rate - concerning for network security"
            else:
                security = "NEUTRAL"
                trend = "STABLE"
                interpretation = "Neutral hash rate - stable network security"
            
            # Analyze miner behavior
            if miner_flows_change < -10:
                miner_behavior = "HODLING"
                miner_interpretation = "Miners holding BTC - bullish signal"
            elif miner_flows_change > 10:
                miner_behavior = "SELLING"
                miner_interpretation = "Miners selling BTC - bearish signal"
            else:
                miner_behavior = "NEUTRAL"
                miner_interpretation = "Normal miner behavior"
            
            return {
                "analysis": f"{security}_{trend}",
                "security": security,
                "trend": trend,
                "interpretation": interpretation,
                "miner_behavior": miner_behavior,
                "miner_interpretation": miner_interpretation,
                "hash_rate_change_pct": hash_rate_change,
                "difficulty_change_pct": difficulty_change,
                "miner_flows_change_pct": miner_flows_change
            }
            
        except Exception as e:
            logger.error(f"❌ Mining metrics analysis failed: {e}")
            return {"analysis": "ERROR", "security": "UNKNOWN", "trend": "UNKNOWN"}
    
    def _analyze_network_health(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze network health metrics"""
        try:
            if not network_data or "error" in network_data:
                return {"analysis": "NO_DATA", "health": "UNKNOWN", "congestion": "UNKNOWN"}
            
            tx_count = network_data.get("transaction_count", {})
            tx_volume = network_data.get("transaction_volume", {})
            fees = network_data.get("average_transaction_fee", {})
            mempool = network_data.get("mempool_size", {})
            
            tx_change = tx_count.get("change_24h_pct", 0)
            volume_change = tx_volume.get("change_24h_pct", 0)
            fee_change = fees.get("change_24h_pct", 0)
            mempool_change = mempool.get("change_24h_pct", 0)
            
            # Analyze network health
            if tx_change > 5 and volume_change > 5 and fee_change < -5:
                health = "EXCELLENT"
                congestion = "LOW"
                interpretation = "High activity with low fees - excellent network health"
            elif tx_change > 2 and volume_change > 2 and fee_change < 0:
                health = "GOOD"
                congestion = "LOW"
                interpretation = "Good activity with reasonable fees"
            elif tx_change > 0 and volume_change > 0:
                health = "FAIR"
                congestion = "MODERATE"
                interpretation = "Moderate network activity"
            elif fee_change > 10 or mempool_change > 20:
                health = "POOR"
                congestion = "HIGH"
                interpretation = "High fees and congestion - poor network health"
            else:
                health = "NEUTRAL"
                congestion = "MODERATE"
                interpretation = "Neutral network conditions"
            
            return {
                "analysis": f"{health}_{congestion}",
                "health": health,
                "congestion": congestion,
                "interpretation": interpretation,
                "tx_count_change_pct": tx_change,
                "volume_change_pct": volume_change,
                "fee_change_pct": fee_change,
                "mempool_change_pct": mempool_change
            }
            
        except Exception as e:
            logger.error(f"❌ Network health analysis failed: {e}")
            return {"analysis": "ERROR", "health": "UNKNOWN", "congestion": "UNKNOWN"}
    
    def _analyze_whale_activity(self, flows_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze whale activity patterns"""
        try:
            if not flows_data or "error" in flows_data:
                return {"analysis": "NO_DATA", "activity": "UNKNOWN", "impact": "UNKNOWN"}
            
            # Mock whale activity analysis (in production, use Glassnode whale metrics)
            whale_activity = {
                "large_transactions": {
                    "count_24h": 45,  # Transactions > 100 BTC
                    "volume_24h": 8500,  # Total volume in BTC
                    "change_24h": 8,  # Change from yesterday
                    "trend": "INCREASING"
                },
                "whale_movements": {
                    "to_exchanges": 1250,  # Large amounts to exchanges
                    "from_exchanges": 980,  # Large amounts from exchanges
                    "net_movement": 270,  # Net movement
                    "direction": "TO_EXCHANGES"
                },
                "timestamp": time.time(),
                "data_source": "mock_whale_activity"
            }
            
            net_movement = whale_activity["whale_movements"]["net_movement"]
            direction = whale_activity["whale_movements"]["direction"]
            
            # Analyze whale impact
            if direction == "TO_EXCHANGES" and net_movement > 500:
                activity = "HIGH_SELLING"
                impact = "BEARISH"
                interpretation = "Large whale movements to exchanges - bearish signal"
            elif direction == "FROM_EXCHANGES" and net_movement > 500:
                activity = "HIGH_ACCUMULATION"
                impact = "BULLISH"
                interpretation = "Large whale movements from exchanges - bullish signal"
            elif abs(net_movement) > 200:
                activity = "MODERATE"
                impact = "NEUTRAL"
                interpretation = "Moderate whale activity - neutral impact"
            else:
                activity = "LOW"
                impact = "MINIMAL"
                interpretation = "Low whale activity - minimal impact"
            
            return {
                "analysis": f"{activity}_{impact}",
                "activity": activity,
                "impact": impact,
                "interpretation": interpretation,
                "large_tx_count": whale_activity["large_transactions"]["count_24h"],
                "whale_net_movement": net_movement,
                "whale_direction": direction
            }
            
        except Exception as e:
            logger.error(f"❌ Whale activity analysis failed: {e}")
            return {"analysis": "ERROR", "activity": "UNKNOWN", "impact": "UNKNOWN"}
    
    def _determine_onchain_sentiment(self, flows_data: Dict[str, Any], addresses_data: Dict[str, Any], mining_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall on-chain sentiment"""
        try:
            # Collect sentiment indicators
            sentiment_indicators = []
            
            # Exchange flow sentiment
            if flows_data and "net_flow" in flows_data:
                net_flow = flows_data["net_flow"]
                if net_flow.get("direction") == "OUTFLOW" and net_flow.get("btc", 0) > 50:
                    sentiment_indicators.append("ACCUMULATION")
                elif net_flow.get("direction") == "INFLOW" and net_flow.get("btc", 0) > 50:
                    sentiment_indicators.append("DISTRIBUTION")
            
            # Address activity sentiment
            if addresses_data and "daily_active" in addresses_data:
                daily_change = addresses_data["daily_active"].get("change_24h_pct", 0)
                if daily_change > 3:
                    sentiment_indicators.append("HIGH_ACTIVITY")
                elif daily_change < -3:
                    sentiment_indicators.append("LOW_ACTIVITY")
            
            # Mining sentiment
            if mining_data and "hash_rate" in mining_data:
                hash_rate_change = mining_data["hash_rate"].get("change_24h_pct", 0)
                if hash_rate_change > 3:
                    sentiment_indicators.append("STRONG_SECURITY")
                elif hash_rate_change < -3:
                    sentiment_indicators.append("WEAK_SECURITY")
            
            # Determine overall sentiment
            bullish_indicators = ["ACCUMULATION", "HIGH_ACTIVITY", "STRONG_SECURITY"]
            bearish_indicators = ["DISTRIBUTION", "LOW_ACTIVITY", "WEAK_SECURITY"]
            
            bullish_count = sum(1 for indicator in sentiment_indicators if indicator in bullish_indicators)
            bearish_count = sum(1 for indicator in sentiment_indicators if indicator in bearish_indicators)
            
            if bullish_count > bearish_count:
                sentiment = "BULLISH"
                strength = "STRONG" if bullish_count >= 2 else "MODERATE"
            elif bearish_count > bullish_count:
                sentiment = "BEARISH"
                strength = "STRONG" if bearish_count >= 2 else "MODERATE"
            else:
                sentiment = "NEUTRAL"
                strength = "WEAK"
            
            return {
                "sentiment": sentiment,
                "strength": strength,
                "indicators": sentiment_indicators,
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "confidence": min(1.0, (bullish_count + bearish_count) / 3)
            }
            
        except Exception as e:
            logger.error(f"❌ On-chain sentiment determination failed: {e}")
            return {"sentiment": "UNKNOWN", "strength": "WEAK", "indicators": [], "confidence": 0.0}
    
    def _update_metrics_history(self, analysis: Dict[str, Any]):
        """Update metrics history for trend analysis"""
        try:
            self._metrics_history.append(analysis)
            
            # Keep only recent history
            if len(self._metrics_history) > self._max_history:
                self._metrics_history = self._metrics_history[-self._max_history:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update metrics history: {e}")
    
    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if still valid"""
        if key in self._data_cache and key in self._cache_timestamps:
            if time.time() - self._cache_timestamps[key] < self._cache_duration:
                return self._data_cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict[str, Any]):
        """Cache data with timestamp"""
        self._data_cache[key] = data
        self._cache_timestamps[key] = time.time()
    
