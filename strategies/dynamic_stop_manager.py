#!/usr/bin/env python3
"""
Dynamic Stop Loss Manager - Volatility-Aware Trailing Stops
Prevents getting stopped out by Bitcoin's natural volatility while protecting profits
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger
import threading
from collections import deque

class DynamicStopManager:
    """Manages dynamic stop losses with Bitcoin volatility awareness"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # High-frequency monitoring
        self.check_interval = 3  # Check every 3 seconds (2-5 sec range)
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Volatility-aware stop parameters
        self.VOLATILITY_STOPS = {
            "low_volatility": {      # <0.2% volatility
                "base_distance": 0.008,     # 0.8% base stop
                "trailing_trigger": 0.012,  # Start trailing at 1.2% profit
                "trailing_distance": 0.006, # Trail 0.6% behind
                "max_adjustments": 3,
                "cooldown": 60  # 1 minute between adjustments
            },
            "medium_volatility": {   # 0.2%-0.6% volatility  
                "base_distance": 0.012,     # 1.2% base stop
                "trailing_trigger": 0.018,  # Start trailing at 1.8% profit
                "trailing_distance": 0.009, # Trail 0.9% behind
                "max_adjustments": 4,
                "cooldown": 45  # 45 seconds
            },
            "high_volatility": {     # 0.6%-1.0% volatility
                "base_distance": 0.020,     # 2.0% base stop 
                "trailing_trigger": 0.025,  # Start trailing at 2.5% profit
                "trailing_distance": 0.015, # Trail 1.5% behind
                "max_adjustments": 5,
                "cooldown": 30  # 30 seconds
            },
            "extreme_volatility": { # >1.0% volatility
                "base_distance": 0.035,     # 3.5% base stop
                "trailing_trigger": 0.040,  # Start trailing at 4.0% profit  
                "trailing_distance": 0.025, # Trail 2.5% behind
                "max_adjustments": 6,
                "cooldown": 20  # 20 seconds
            }
        }
        
        # Bitcoin-specific volatility patterns
        self.BTC_PATTERNS = {
            "normal_noise": 0.003,      # 0.3% normal fluctuation
            "minor_swing": 0.008,       # 0.8% minor swing
            "major_swing": 0.015,       # 1.5% major swing
            "crash_protection": 0.025   # 2.5% crash threshold
        }
        
        # Position tracking
        self.position_data = {}  # Store enhanced position data
        self.price_history = deque(maxlen=100)  # Last 100 price points
        self.volatility_history = deque(maxlen=20)  # Last 20 volatility readings
        
        logger.info("🛡️ Dynamic Stop Manager initialized - Bitcoin volatility aware")
    
    def start_monitoring(self, bot_instance):
        """Start high-frequency stop monitoring (every 2-5 seconds)"""
        if self.is_monitoring:
            logger.warning("Stop monitoring already active")
            return
        
        self.is_monitoring = True
        self.bot_instance = bot_instance
        self.monitor_thread = threading.Thread(target=self._monitor_stops, daemon=True)
        self.monitor_thread.start()
        
        logger.success(f"🚨 High-frequency stop monitoring started - checking every {self.check_interval}s")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("🛡️ Stop monitoring stopped")
    
    def _monitor_stops(self):
        """Main monitoring loop - runs every 2-5 seconds"""
        while self.is_monitoring:
            try:
                # Get current price
                current_price = self.bot_instance.get_hyperliquid_price()
                if not current_price:
                    time.sleep(self.check_interval)
                    continue
                
                # Update price history
                self.price_history.append({
                    "price": current_price,
                    "timestamp": time.time()
                })
                
                # Calculate real-time volatility
                current_volatility = self._calculate_realtime_volatility()
                self.volatility_history.append(current_volatility)
                
                # Check all open positions
                if hasattr(self.bot_instance, 'open_positions'):
                    for position in self.bot_instance.open_positions:
                        self._check_and_adjust_stop(position, current_price, current_volatility)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Stop monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def _calculate_realtime_volatility(self) -> float:
        """Calculate real-time volatility from recent price movements"""
        if len(self.price_history) < 10:
            return 0.003  # Default volatility
        
        # Get prices from last 5 minutes (100 data points at 3-second intervals)  
        try:
            recent_prices = [p["price"] for p in list(self.price_history)[-20:]]  # Last minute
        except (TypeError, KeyError) as e:
            logger.debug(f"Price history access error: {e}")
            return 0.003
        
        if len(recent_prices) < 5:
            return 0.003
        
        # Calculate returns
        returns = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] 
                  for i in range(1, len(recent_prices))]
        
        # Annualized volatility (scale to daily)
        volatility = np.std(returns) * np.sqrt(len(returns))
        return max(0.001, min(0.05, volatility))  # Cap between 0.1% and 5%
    
    def _check_and_adjust_stop(self, position: Dict[str, Any], current_price: float, current_volatility: float):
        """Check and adjust stop loss for a specific position"""
        
        position_id = position.get("trade_id", "unknown")
        side = position["side"]
        entry_price = position["entry_price"]
        current_stop = position.get("current_stop_loss", position.get("stop_price", 0))
        
        # Get volatility regime
        vol_regime = self._get_volatility_regime(current_volatility)
        stop_config = self.VOLATILITY_STOPS[vol_regime]
        
        # Calculate current P&L
        if side == "BUY":
            current_pnl_pct = (current_price - entry_price) / entry_price
        else:
            current_pnl_pct = (entry_price - current_price) / entry_price
        
        # Check if we should trail the stop
        should_trail = current_pnl_pct >= stop_config["trailing_trigger"]
        
        if should_trail:
            new_stop = self._calculate_trailing_stop(
                position, current_price, current_volatility, vol_regime
            )
            
            # Check if adjustment is meaningful and safe
            if self._is_valid_stop_adjustment(position, current_stop, new_stop, side):
                self._update_position_stop(position, new_stop, vol_regime, current_pnl_pct)
        
        # Check for volatility spike protection
        elif current_volatility > 0.015:  # 1.5% volatility spike
            self._apply_volatility_protection(position, current_price, current_volatility)
    
    def _get_volatility_regime(self, volatility: float) -> str:
        """Determine current volatility regime"""
        if volatility > 0.010:
            return "extreme_volatility"
        elif volatility > 0.006:
            return "high_volatility" 
        elif volatility > 0.002:
            return "medium_volatility"
        else:
            return "low_volatility"
    
    def _calculate_trailing_stop(self, position: Dict[str, Any], current_price: float, 
                               volatility: float, vol_regime: str) -> float:
        """Calculate new trailing stop based on volatility regime"""
        
        side = position["side"]
        entry_price = position["entry_price"]
        stop_config = self.VOLATILITY_STOPS[vol_regime]
        
        # Base trailing distance
        trailing_distance = stop_config["trailing_distance"]
        
        # Volatility adjustment - wider stops in high volatility
        volatility_multiplier = max(1.0, volatility / 0.004)  # Scale based on 0.4% base
        adjusted_distance = trailing_distance * volatility_multiplier
        
        # Bitcoin pattern adjustment
        if volatility > self.BTC_PATTERNS["major_swing"]:
            # Major swing - give more room
            adjusted_distance *= 1.5
            logger.info(f"🌊 Major BTC swing detected - widening stop by 50%")
        elif volatility > self.BTC_PATTERNS["minor_swing"]:
            # Minor swing - slight adjustment
            adjusted_distance *= 1.2
        
        # Calculate new stop
        if side == "BUY":
            new_stop = current_price * (1 - adjusted_distance)
        else:
            new_stop = current_price * (1 + adjusted_distance)
        
        return new_stop
    
    def _is_valid_stop_adjustment(self, position: Dict[str, Any], current_stop: float, 
                                new_stop: float, side: str) -> bool:
        """Validate if stop adjustment is safe and meaningful"""
        
        # Check cooldown
        last_adjustment = position.get("last_stop_adjustment", 0)
        vol_regime = self._get_volatility_regime(self._calculate_realtime_volatility())
        cooldown = self.VOLATILITY_STOPS[vol_regime]["cooldown"]
        
        if time.time() - last_adjustment < cooldown:
            return False
        
        # Check adjustment count
        adjustment_count = position.get("stop_adjustment_count", 0)
        max_adjustments = self.VOLATILITY_STOPS[vol_regime]["max_adjustments"]
        
        if adjustment_count >= max_adjustments:
            return False
        
        # Check direction - only move stops favorably
        if side == "BUY":
            # For longs, only move stop up (never down)
            if new_stop <= current_stop:
                return False
        else:
            # For shorts, only move stop down (never up)
            if new_stop >= current_stop:
                return False
        
        # Check meaningful change (at least 0.2%)
        stop_change_pct = abs(new_stop - current_stop) / current_stop
        if stop_change_pct < 0.002:
            return False
        
        return True
    
    def _update_position_stop(self, position: Dict[str, Any], new_stop: float, 
                            vol_regime: str, current_pnl_pct: float):
        """Update position with new stop loss"""
        
        old_stop = position.get("current_stop_loss", position.get("stop_price", 0))
        position["current_stop_loss"] = new_stop
        position["last_stop_adjustment"] = time.time()
        position["stop_adjustment_count"] = position.get("stop_adjustment_count", 0) + 1
        
        # Calculate improvement
        entry_price = position["entry_price"]
        side = position["side"]
        
        if side == "BUY":
            old_protection = (old_stop - entry_price) / entry_price
            new_protection = (new_stop - entry_price) / entry_price
        else:
            old_protection = (entry_price - old_stop) / entry_price
            new_protection = (entry_price - new_stop) / entry_price
        
        improvement = new_protection - old_protection
        
        logger.success(f"🛡️ STOP ADJUSTED - {position['trade_id']}")
        logger.info(f"   Old Stop: ${old_stop:,.2f}")
        logger.info(f"   New Stop: ${new_stop:,.2f}")
        logger.info(f"   Improvement: {improvement*100:+.2f}%")
        logger.info(f"   Current P&L: {current_pnl_pct*100:+.1f}%")
        logger.info(f"   Volatility: {vol_regime}")
    
    def _apply_volatility_protection(self, position: Dict[str, Any], current_price: float, volatility: float):
        """Apply extra protection during volatility spikes"""
        
        # Don't adjust during extreme volatility to avoid whipsaws
        if volatility > self.BTC_PATTERNS["crash_protection"]:
            logger.warning(f"🌪️ EXTREME VOLATILITY DETECTED: {volatility*100:.1f}% - Stop adjustments paused")
            return
        
        # For high volatility, ensure stop is not too tight
        entry_price = position["entry_price"]
        side = position["side"]
        current_stop = position.get("current_stop_loss", position.get("stop_price", 0))
        
        # Calculate minimum safe distance based on volatility
        min_distance = max(self.BTC_PATTERNS["normal_noise"], volatility * 2)
        
        if side == "BUY":
            min_safe_stop = current_price * (1 - min_distance)
            if current_stop > min_safe_stop:
                # Stop is too tight for current volatility
                new_stop = min_safe_stop
                position["current_stop_loss"] = new_stop
                logger.warning(f"⚠️ VOLATILITY PROTECTION: Widened stop from ${current_stop:,.2f} to ${new_stop:,.2f}")
        else:
            min_safe_stop = current_price * (1 + min_distance)
            if current_stop < min_safe_stop:
                new_stop = min_safe_stop
                position["current_stop_loss"] = new_stop
                logger.warning(f"⚠️ VOLATILITY PROTECTION: Widened stop from ${current_stop:,.2f} to ${new_stop:,.2f}")


class GlobalVolumeAggregator:
    """Real-time global BTC volume aggregation from all major exchanges"""
    
    def __init__(self):
        self.exchanges = {
            "binance": {
                "websocket": "wss://stream.binance.com:9443/ws/btcusdt@ticker",
                "rest_api": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
                "weight": 0.35  # Binance has ~35% of global volume
            },
            "coinbase": {
                "websocket": "wss://ws-feed.exchange.coinbase.com",
                "rest_api": "https://api.exchange.coinbase.com/products/BTC-USD/ticker",
                "weight": 0.15  # ~15% of global volume
            },
            "okx": {
                "rest_api": "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
                "weight": 0.20  # ~20% of global volume
            },
            "kraken": {
                "rest_api": "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
                "weight": 0.10  # ~10% of global volume
            },
            "bybit": {
                "rest_api": "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT",
                "weight": 0.12  # ~12% of global volume
            },
            "bitfinex": {
                "rest_api": "https://api-pub.bitfinex.com/v2/ticker/tBTCUSD",
                "weight": 0.08  # ~8% of global volume
            }
        }
        
        self.current_global_volume = 0
        self.volume_by_exchange = {}
        self.last_update = 0
        self.update_interval = 5  # Update every 5 seconds
        
        logger.info("🌍 Global Volume Aggregator initialized")
    
    def get_realtime_global_volume(self) -> Dict[str, Any]:
        """Get current second global BTC trading volume"""
        current_time = time.time()
        
        if current_time - self.last_update < self.update_interval:
            return {
                "global_volume_per_second": self.current_global_volume,
                "volume_by_exchange": self.volume_by_exchange,
                "last_update": self.last_update,
                "status": "cached"
            }
        
        try:
            import requests
            import json
            
            total_volume = 0
            exchange_volumes = {}
            successful_exchanges = 0
            
            # Get volume from all exchanges
            for exchange_name, exchange_config in self.exchanges.items():
                try:
                    # Add SSL verification fix for problematic exchanges
                    response = requests.get(exchange_config["rest_api"], timeout=3, verify=False)
                    if response.status_code == 200:
                        volume = self._parse_exchange_volume(exchange_name, response.json())
                        if volume > 0:
                            # Convert 24h volume to per-second
                            volume_per_second = volume / (24 * 60 * 60)
                            weighted_volume = volume_per_second * exchange_config["weight"]
                            
                            total_volume += weighted_volume
                            exchange_volumes[exchange_name] = {
                                "volume_24h": volume,
                                "volume_per_second": volume_per_second,
                                "weighted_contribution": weighted_volume,
                                "weight": exchange_config["weight"],
                                "status": "success"
                            }
                            successful_exchanges += 1
                
                except Exception as e:
                    exchange_volumes[exchange_name] = {
                        "status": "error",
                        "error": str(e)[:50]  # Truncate long error messages
                    }
                    # Only log SSL errors as debug, not warnings
                    if "SSL" in str(e) or "ssl" in str(e).lower():
                        logger.debug(f"Exchange {exchange_name} SSL issue (ignoring): {str(e)[:50]}...")
                    else:
                        logger.debug(f"Exchange {exchange_name} volume fetch failed: {e}")
            
            # Extrapolate total global volume
            if successful_exchanges > 0:
                # Account for exchanges we couldn't reach
                coverage_ratio = sum(self.exchanges[ex]["weight"] for ex in exchange_volumes 
                                   if exchange_volumes[ex].get("status") == "success")
                
                if coverage_ratio > 0.5:  # We have >50% coverage
                    estimated_global_volume = total_volume / coverage_ratio
                else:
                    estimated_global_volume = total_volume * 2  # Conservative estimate
                
                self.current_global_volume = estimated_global_volume
                self.volume_by_exchange = exchange_volumes
                self.last_update = current_time
                
                logger.info(f"🌍 Global BTC Volume: {estimated_global_volume:.1f} BTC/second ({coverage_ratio:.1%} coverage)")
                
                return {
                    "global_volume_per_second": estimated_global_volume,
                    "volume_by_exchange": exchange_volumes,
                    "coverage_ratio": coverage_ratio,
                    "successful_exchanges": successful_exchanges,
                    "total_exchanges": len(self.exchanges),
                    "last_update": current_time,
                    "status": "success"
                }
            
            return {
                "global_volume_per_second": 0,
                "status": "error",
                "reason": "No exchanges responded successfully"
            }
            
        except Exception as e:
            logger.error(f"Global volume aggregation error: {e}")
            return {
                "global_volume_per_second": self.current_global_volume,
                "status": "error", 
                "reason": str(e)
            }
    
    def _parse_exchange_volume(self, exchange_name: str, data: Any) -> float:
        """Parse volume data from different exchange API formats"""
        try:
            if exchange_name == "binance":
                return float(data.get("volume", 0))
            elif exchange_name == "coinbase":
                return float(data.get("volume", 0))
            elif exchange_name == "okx":
                return float(data.get("data", [{}])[0].get("vol24h", 0))
            elif exchange_name == "kraken":
                ticker_data = data.get("result", {})
                xbt_data = ticker_data.get("XXBTZUSD", {})
                return float(xbt_data.get("v", [0, 0])[1])  # 24h volume
            elif exchange_name == "bybit":
                return float(data.get("result", {}).get("list", [{}])[0].get("volume24h", 0))
            elif exchange_name == "bitfinex":
                return float(data[7]) if len(data) > 7 else 0  # Volume is at index 7
            
            return 0
            
        except Exception as e:
            logger.debug(f"Failed to parse {exchange_name} volume: {e}")
            return 0


class BlockchainDataAnalyzer:
    """Real-time blockchain data for enhanced trading intelligence"""
    
    def __init__(self):
        self.apis = {
            "blockchair": "https://api.blockchair.com/bitcoin/stats",
            "blockchain_info": "https://blockchain.info/q/24hrtransactioncount", 
            "mempool_space": "https://mempool.space/api/v1/fees/recommended",
            "glassnode": None  # Would require paid API key
        }
        
        self.cache = {}
        self.cache_duration = 30  # 30 second cache
        
        logger.info("⛓️ Blockchain Data Analyzer initialized")
    
    def get_onchain_sentiment(self) -> Dict[str, Any]:
        """Get on-chain sentiment indicators"""
        try:
            import requests
            
            sentiment_data = {}
            
            # 1. Transaction activity (bullish indicator)
            try:
                response = requests.get(self.apis["blockchain_info"], timeout=5)
                if response.status_code == 200:
                    tx_count_24h = int(response.text)
                    
                    # Normal Bitcoin processes ~300k transactions/day
                    if tx_count_24h > 350000:
                        tx_sentiment = "BULLISH"
                    elif tx_count_24h > 250000:
                        tx_sentiment = "NEUTRAL"
                    else:
                        tx_sentiment = "BEARISH"
                    
                    sentiment_data["transaction_activity"] = {
                        "count_24h": tx_count_24h,
                        "sentiment": tx_sentiment,
                        "source": "blockchain.info"
                    }
            except Exception as e:
                logger.debug(f"Transaction data fetch failed: {e}")
            
            # 2. Network fees (demand indicator)
            try:
                response = requests.get(self.apis["mempool_space"], timeout=5)
                if response.status_code == 200:
                    fee_data = response.json()
                    fast_fee = fee_data.get("fastestFee", 1)
                    
                    # High fees = high demand = bullish
                    if fast_fee > 50:
                        fee_sentiment = "VERY_BULLISH"
                    elif fast_fee > 20:
                        fee_sentiment = "BULLISH"
                    elif fast_fee > 10:
                        fee_sentiment = "NEUTRAL"
                    else:
                        fee_sentiment = "BEARISH"
                    
                    sentiment_data["network_fees"] = {
                        "fastest_fee": fast_fee,
                        "sentiment": fee_sentiment,
                        "source": "mempool.space"
                    }
            except Exception as e:
                logger.debug(f"Fee data fetch failed: {e}")
            
            # 3. Overall blockchain sentiment
            sentiments = [data.get("sentiment", "NEUTRAL") for data in sentiment_data.values()]
            bullish_count = sum(1 for s in sentiments if "BULLISH" in s)
            bearish_count = sum(1 for s in sentiments if "BEARISH" in s)
            
            if bullish_count > bearish_count:
                overall_sentiment = "BULLISH"
            elif bearish_count > bullish_count:
                overall_sentiment = "BEARISH"
            else:
                overall_sentiment = "NEUTRAL"
            
            return {
                "overall_sentiment": overall_sentiment,
                "confidence": len(sentiment_data) / 2,  # Confidence based on data availability
                "indicators": sentiment_data,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Blockchain sentiment analysis error: {e}")
            return {
                "overall_sentiment": "UNKNOWN",
                "confidence": 0,
                "error": str(e)
            }