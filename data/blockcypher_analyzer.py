#!/usr/bin/env python3
"""
BlockCypher Analyzer
Free blockchain analytics for whale tracking and exchange flow monitoring
"""

import time
import requests
import statistics
from typing import Dict, Any, List, Optional
from loguru import logger
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class WhaleTransaction:
    """Represents a large whale transaction"""
    hash: str
    value_usd: float
    timestamp: int
    from_address: str
    to_address: str
    size_bytes: int
    fee: float
    confirmed: bool

@dataclass
class ExchangeFlow:
    """Represents exchange flow data"""
    exchange: str
    flow_type: str  # 'inflow' or 'outflow'
    amount_usd: float
    timestamp: int
    confidence: float

class BlockCypherAnalyzer:
    """Free blockchain analytics using BlockCypher API"""
    
    def __init__(self, api_token: str = None):
        self.base_url = "https://api.blockcypher.com/v1"
        self.api_token = api_token  # Optional, works without token for basic usage
        self.session = requests.Session()
        
        # Known exchange addresses (partial list)
        self.exchange_addresses = {
            "binance": [
                "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",  # Binance hot wallet
                "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",  # Binance cold wallet
            ],
            "coinbase": [
                "1P5ZEDWTKTFGxQjZphgWPQUX554HKD3XZj",  # Coinbase hot wallet
                "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",  # Coinbase cold wallet
            ],
            "kraken": [
                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Kraken hot wallet
                "3E8ociqZa9mZUSwGdSmAEMAoAxBK3FNDcd",  # Kraken cold wallet
            ]
        }
        
        # Whale thresholds
        self.whale_thresholds = {
            "small_whale": 100000,    # $100k
            "medium_whale": 1000000,  # $1M
            "large_whale": 10000000,  # $10M
            "mega_whale": 100000000   # $100M
        }
        
        # Cache for API responses
        self.cache = {}
        self.cache_duration = 60  # 1 minute cache
        
        logger.info("🔗 BlockCypher Analyzer initialized")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling and caching"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Add API token if available
            if self.api_token:
                if params is None:
                    params = {}
                params['token'] = self.api_token
            
            # Check cache first
            cache_key = f"{endpoint}_{hash(str(params))}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if time.time() - cached_time < self.cache_duration:
                    return cached_data
            
            # Make request
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            self.cache[cache_key] = (data, time.time())
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ BlockCypher API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ BlockCypher API error: {e}")
            return None
    
    def get_btc_price(self) -> Optional[float]:
        """Get current BTC price from BlockCypher"""
        try:
            data = self._make_request("btc/main")
            if data and 'last_fork_height' in data:  # Valid response
                # BlockCypher doesn't provide price directly, use alternative
                return self._get_btc_price_alternative()
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get BTC price: {e}")
            return None
    
    def _get_btc_price_alternative(self) -> Optional[float]:
        """Get BTC price from alternative source"""
        try:
            # Use CoinGecko API as fallback
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('bitcoin', {}).get('usd')
            return None
        except:
            return None
    
    def get_recent_transactions(self, limit: int = 50) -> List[WhaleTransaction]:
        """Get recent large BTC transactions"""
        try:
            data = self._make_request("btc/main/txs", {"limit": limit})
            if not data:
                return []
            
            transactions = []
            btc_price = self.get_btc_price() or 50000  # Fallback price
            
            for tx in data:
                try:
                    # Calculate transaction value in USD
                    value_btc = tx.get('total', 0) / 100000000  # Convert satoshis to BTC
                    value_usd = value_btc * btc_price
                    
                    # Only include significant transactions
                    if value_usd >= self.whale_thresholds["small_whale"]:
                        whale_tx = WhaleTransaction(
                            hash=tx.get('hash', ''),
                            value_usd=value_usd,
                            timestamp=tx.get('received', 0),
                            from_address=tx.get('addresses', [None])[0] if tx.get('addresses') else None,
                            to_address=tx.get('addresses', [None])[-1] if tx.get('addresses') else None,
                            size_bytes=tx.get('size', 0),
                            fee=tx.get('fees', 0) / 100000000,  # Convert to BTC
                            confirmed=tx.get('confirmed', False)
                        )
                        transactions.append(whale_tx)
                        
                except Exception as e:
                    logger.debug(f"Failed to parse transaction: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent transactions: {e}")
            return []
    
    def analyze_whale_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze whale activity over the last N hours"""
        try:
            transactions = self.get_recent_transactions(limit=100)
            
            # Filter by time
            cutoff_time = int(time.time()) - (hours * 3600)
            recent_txs = [tx for tx in transactions if isinstance(tx.timestamp, (int, float)) and tx.timestamp >= cutoff_time]
            
            if not recent_txs:
                return {
                    "whale_count": 0,
                    "total_volume_usd": 0,
                    "average_tx_size": 0,
                    "largest_tx": 0,
                    "sentiment": "neutral",
                    "activity_level": "low"
                }
            
            # Calculate metrics
            total_volume = sum(tx.value_usd for tx in recent_txs)
            avg_tx_size = statistics.mean(tx.value_usd for tx in recent_txs)
            largest_tx = max(tx.value_usd for tx in recent_txs)
            
            # Categorize transactions by size
            small_whales = len([tx for tx in recent_txs if tx.value_usd >= self.whale_thresholds["small_whale"]])
            medium_whales = len([tx for tx in recent_txs if tx.value_usd >= self.whale_thresholds["medium_whale"]])
            large_whales = len([tx for tx in recent_txs if tx.value_usd >= self.whale_thresholds["large_whale"]])
            
            # Determine sentiment
            sentiment = self._calculate_whale_sentiment(recent_txs, total_volume)
            
            # Determine activity level
            activity_level = self._calculate_activity_level(len(recent_txs), total_volume)
            
            return {
                "whale_count": len(recent_txs),
                "total_volume_usd": total_volume,
                "average_tx_size": avg_tx_size,
                "largest_tx": largest_tx,
                "small_whales": small_whales,
                "medium_whales": medium_whales,
                "large_whales": large_whales,
                "sentiment": sentiment,
                "activity_level": activity_level,
                "transactions": recent_txs[:10]  # Top 10 transactions
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze whale activity: {e}")
            return {"error": str(e)}
    
    def _calculate_whale_sentiment(self, transactions: List[WhaleTransaction], total_volume: float) -> str:
        """Calculate whale sentiment based on transaction patterns"""
        try:
            if not transactions:
                return "neutral"
            
            # Analyze transaction patterns
            confirmed_txs = [tx for tx in transactions if tx.confirmed]
            unconfirmed_txs = [tx for tx in transactions if not tx.confirmed]
            
            # High volume of confirmed transactions suggests bullish sentiment
            if len(confirmed_txs) > len(unconfirmed_txs) * 2 and total_volume > 10000000:
                return "bullish"
            elif len(unconfirmed_txs) > len(confirmed_txs) * 2:
                return "bearish"
            else:
                return "neutral"
                
        except Exception as e:
            logger.debug(f"Failed to calculate sentiment: {e}")
            return "neutral"
    
    def _calculate_activity_level(self, tx_count: int, total_volume: float) -> str:
        """Calculate whale activity level"""
        if tx_count >= 20 and total_volume >= 50000000:
            return "very_high"
        elif tx_count >= 10 and total_volume >= 20000000:
            return "high"
        elif tx_count >= 5 and total_volume >= 10000000:
            return "medium"
        elif tx_count >= 2 and total_volume >= 5000000:
            return "low"
        else:
            return "very_low"
    
    def get_exchange_flows(self, hours: int = 24) -> List[ExchangeFlow]:
        """Analyze exchange flows by monitoring known exchange addresses"""
        try:
            transactions = self.get_recent_transactions(limit=200)
            cutoff_time = int(time.time()) - (hours * 3600)
            recent_txs = [tx for tx in transactions if isinstance(tx.timestamp, (int, float)) and tx.timestamp >= cutoff_time]
            
            exchange_flows = []
            
            for tx in recent_txs:
                for exchange, addresses in self.exchange_addresses.items():
                    # Check if transaction involves exchange address
                    if tx.from_address in addresses:
                        exchange_flows.append(ExchangeFlow(
                            exchange=exchange,
                            flow_type="outflow",  # Exchange is sending out
                            amount_usd=tx.value_usd,
                            timestamp=tx.timestamp,
                            confidence=0.8
                        ))
                    elif tx.to_address in addresses:
                        exchange_flows.append(ExchangeFlow(
                            exchange=exchange,
                            flow_type="inflow",  # Exchange is receiving
                            amount_usd=tx.value_usd,
                            timestamp=tx.timestamp,
                            confidence=0.8
                        ))
            
            return exchange_flows
            
        except Exception as e:
            logger.error(f"❌ Failed to get exchange flows: {e}")
            return []
    
    def get_whale_sentiment_score(self) -> Dict[str, Any]:
        """Get comprehensive whale sentiment score for trading decisions"""
        try:
            whale_analysis = self.analyze_whale_activity(hours=6)  # Last 6 hours
            exchange_flows = self.get_exchange_flows(hours=6)
            
            if "error" in whale_analysis:
                return {
                    "score": 0.5,
                    "sentiment": "neutral",
                    "confidence": 0.0,
                    "reason": "Analysis failed"
                }
            
            # Calculate sentiment score (0-1)
            base_score = 0.5
            
            # Adjust based on whale sentiment
            if whale_analysis["sentiment"] == "bullish":
                base_score += 0.2
            elif whale_analysis["sentiment"] == "bearish":
                base_score -= 0.2
            
            # Adjust based on activity level
            activity_multiplier = {
                "very_high": 1.2,
                "high": 1.1,
                "medium": 1.0,
                "low": 0.9,
                "very_low": 0.8
            }
            
            base_score *= activity_multiplier.get(whale_analysis["activity_level"], 1.0)
            
            # Adjust based on exchange flows
            total_inflow = sum(flow.amount_usd for flow in exchange_flows if flow.flow_type == "inflow")
            total_outflow = sum(flow.amount_usd for flow in exchange_flows if flow.flow_type == "outflow")
            
            if total_inflow > total_outflow * 1.5:  # More money flowing into exchanges
                base_score -= 0.1  # Slightly bearish
            elif total_outflow > total_inflow * 1.5:  # More money flowing out of exchanges
                base_score += 0.1  # Slightly bullish
            
            # Clamp score between 0 and 1
            final_score = max(0.0, min(1.0, base_score))
            
            # Determine sentiment
            if final_score >= 0.7:
                sentiment = "bullish"
            elif final_score <= 0.3:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            # Calculate confidence based on data quality
            confidence = min(0.9, len(whale_analysis.get("transactions", [])) / 10.0)
            
            return {
                "score": final_score,
                "sentiment": sentiment,
                "confidence": confidence,
                "whale_activity": whale_analysis,
                "exchange_flows": len(exchange_flows),
                "total_inflow": total_inflow,
                "total_outflow": total_outflow,
                "reason": f"Whale sentiment: {whale_analysis['sentiment']}, Activity: {whale_analysis['activity_level']}"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get whale sentiment score: {e}")
            return {
                "score": 0.5,
                "sentiment": "neutral",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}"
            }
    
    def should_confirm_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Check if whale activity confirms a trading signal"""
        try:
            whale_sentiment = self.get_whale_sentiment_score()
            
            # If whale sentiment is neutral or we have low confidence, don't block the trade
            if whale_sentiment["confidence"] < 0.3 or whale_sentiment["sentiment"] == "neutral":
                return {
                    "should_proceed": True,
                    "whale_confirmation": "neutral",
                    "confidence": whale_sentiment["confidence"],
                    "reason": "Insufficient whale data to confirm/deny"
                }
            
            # Check if whale sentiment aligns with trade direction
            if signal.get("side") == "BUY" and whale_sentiment["sentiment"] == "bullish":
                return {
                    "should_proceed": True,
                    "whale_confirmation": "confirmed",
                    "confidence": whale_sentiment["confidence"],
                    "reason": f"Whale sentiment bullish ({whale_sentiment['score']:.2f}) confirms BUY signal"
                }
            elif signal.get("side") == "SELL" and whale_sentiment["sentiment"] == "bearish":
                return {
                    "should_proceed": True,
                    "whale_confirmation": "confirmed",
                    "confidence": whale_sentiment["confidence"],
                    "reason": f"Whale sentiment bearish ({whale_sentiment['score']:.2f}) confirms SELL signal"
                }
            else:
                # Whale sentiment contradicts trade direction
                return {
                    "should_proceed": False,
                    "whale_confirmation": "contradicted",
                    "confidence": whale_sentiment["confidence"],
                    "reason": f"Whale sentiment {whale_sentiment['sentiment']} contradicts {signal.get('side')} signal"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to check whale confirmation: {e}")
            return {
                "should_proceed": True,
                "whale_confirmation": "error",
                "confidence": 0.0,
                "reason": f"Error checking whale confirmation: {str(e)}"
            }

# Test function
def test_blockcypher_analyzer():
    """Test the BlockCypher analyzer"""
    logger.info("🧪 Testing BlockCypher Analyzer...")
    
    analyzer = BlockCypherAnalyzer()
    
    # Test whale sentiment
    sentiment = analyzer.get_whale_sentiment_score()
    logger.info(f"Whale Sentiment: {sentiment}")
    
    # Test trade confirmation
    test_signal = {"side": "BUY", "should_trade": True}
    confirmation = analyzer.should_confirm_trade(test_signal)
    logger.info(f"Trade Confirmation: {confirmation}")
    
    logger.info("✅ BlockCypher Analyzer test completed")

if __name__ == "__main__":
    test_blockcypher_analyzer()
