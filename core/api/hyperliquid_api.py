import requests
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from config.config import TradingConfig

class HyperliquidAPI:
    """Hyperliquid API client - simplified to only used methods (dead trading code eliminated)"""
    
    def __init__(self, wallet_address: str = None, wallet_private_key: str = None):
        self.config = TradingConfig()
        self.wallet_address = wallet_address or self.config.WALLET_ADDRESS
        self.wallet_private_key = wallet_private_key or self.config.WALLET_PRIVATE_KEY
        self.base_url = self.config.HYPERLIQUID_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HyperliquidTradingBot/1.0'
        })
        
        # Initialize orderbook data fetcher
        # Analysis functionality moved to dedicated calculators in MarketDataManager
        
        # Only authenticate if not already authenticated
        self._authenticated = False
        if self.wallet_address and self.wallet_private_key:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Hyperliquid API using wallet"""
        try:
            # Skip if already authenticated
            if self._authenticated:
                return
                
            # For wallet-based authentication, we use the wallet address directly
            # No additional headers needed for basic info requests
            logger.debug("Using wallet-based authentication")
            logger.debug(f"Wallet address: {self.wallet_address}")
            
            # Mark as authenticated
            self._authenticated = True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    # ==================================================================================
    # USED METHODS ONLY (6 methods) - All trading methods removed (simulator handles)
    # ==================================================================================

    def get_current_price(self, symbol: str = None) -> Optional[float]:
        """Get current mid-price from WebSocket cache (ultra-fast) or orderbook (fallback)"""
        symbol = symbol or self.config.SYMBOL
        
        # Try WebSocket first (real-time latency)
        try:
            from core.hyperliquid_websocket import get_websocket_instance
            websocket = get_websocket_instance(symbol)
            
            if websocket.is_connected():
                price = websocket.get_current_price()
                if price and price > 0:
                    return price
                else:
                    # WebSocket connected but no price data yet
                    pass
            else:
                # WebSocket not connected, using HTTP fallback
                pass
        except ImportError:
            # WebSocket module not available, using HTTP fallback
            pass
        except Exception as e:
            logger.debug(f"⚠️ WebSocket error: {e}, using HTTP fallback")
        
        # HTTP API fallback (current method)
        try:
            market_data = self.get_market_data(symbol)
            
            if market_data and 'levels' in market_data and len(market_data['levels']) >= 2:
                bids = market_data['levels'][0]
                asks = market_data['levels'][1]
                
                if bids and asks:
                    best_bid = float(bids[0]['px'])
                    best_ask = float(asks[0]['px'])
                    mid_price = (best_bid + best_ask) / 2
                    
                    # logger.debug(f"Current {symbol} price: ${mid_price:,.2f} (Bid: ${best_bid:,.2f}, Ask: ${best_ask:,.2f})")
                    return mid_price
            
            logger.warning(f"Could not get current price for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    def get_market_data(self, symbol: str = None) -> Dict[str, Any]:
        """Get current market data for a symbol"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "l2Book",
                "coin": symbol
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            # logger.debug(f"Retrieved market data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            raise

    def get_orderbook(self, symbol: str = None) -> Dict[str, Any]:
        """Get current orderbook for a symbol"""
        try:
            # Delegate to get_market_data for consistency
            return self.get_market_data(symbol)
            
        except Exception as e:
            logger.error(f"Failed to get orderbook for {symbol}: {e}")
            raise
    
    def get_recent_trades(self, symbol: str = None, limit: int = 100) -> Dict[str, Any]:
        """Get recent trades for a symbol to calculate actual trading volume"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "recentTrades",
                "coin": symbol
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            # logger.debug(f"Retrieved {len(data)} recent trades for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get recent trades for {symbol}: {e}")
            raise

    def get_ongoing_candle(self, symbol: str = None, interval: str = "5m") -> Optional[Dict[str, Any]]:
        """
        Get the current ongoing candle by combining last completed candle with recent trades
        
        This allows us to show the current incomplete candle (e.g., if bot starts at 20:48,
        we can show the candle that started at 20:45 and is still forming until 20:50)
        
        Args:
            symbol: Trading symbol (default: BTC)
            interval: Candle interval (default: 5m)
            
        Returns:
            Ongoing candle dict with OHLCV data or None if unavailable
        """
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Get the last completed candle to use as base
            historical_candles = self.get_historical_candles(symbol, interval, 1)
            if not historical_candles:
                logger.error(f"No historical candles available for ongoing candle")
                return None
            
            last_completed_candle = historical_candles[0]
            
            # Get recent trades to build the ongoing candle
            recent_trades = self.get_recent_trades(symbol, limit=50)
            if not recent_trades:
                logger.warning(f"No recent trades available for ongoing candle")
                return None
            
            # Calculate the current candle start time using UTC for global synchronization
            current_time = time.time()
            interval_seconds = self._get_interval_seconds(interval)
            
            # Use UTC time for global candle synchronization
            import datetime
            utc_dt = datetime.datetime.utcfromtimestamp(current_time)
            utc_minute = utc_dt.minute
            candle_start_minute = (utc_minute // (interval_seconds // 60)) * (interval_seconds // 60)
            candle_start_dt = utc_dt.replace(minute=candle_start_minute, second=0, microsecond=0)
            current_candle_start = candle_start_dt.timestamp()
            
            # Filter trades that belong to the current ongoing candle
            ongoing_trades = []
            for trade in recent_trades:
                trade_time = trade.get('time', 0) / 1000  # Convert from milliseconds
                if trade_time >= current_candle_start:
                    ongoing_trades.append(trade)
            
            if not ongoing_trades:
                logger.debug(f"No trades in current candle period, using last completed candle")
                return last_completed_candle
            
            # Build ongoing candle from trades
            prices = [float(trade.get('px', 0)) for trade in ongoing_trades if trade.get('px')]
            volumes = [float(trade.get('sz', 0)) for trade in ongoing_trades if trade.get('sz')]
            
            if not prices:
                logger.warning(f"No valid price data in ongoing trades")
                return last_completed_candle
            
            # Calculate OHLCV for ongoing candle
            open_price = prices[-1]  # Most recent trade price as open (will be updated)
            high_price = max(prices)
            low_price = min(prices)
            close_price = prices[0]  # First trade in current period as close
            volume = sum(volumes)
            
            # Use the last completed candle's open as the true open for ongoing candle
            if last_completed_candle:
                open_price = last_completed_candle.get('close', open_price)
            
            ongoing_candle = {
                'timestamp': current_candle_start,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'is_ongoing': True,  # Mark as ongoing candle
                'trades_count': len(ongoing_trades),
                'last_trade_time': ongoing_trades[0].get('time', 0) / 1000 if ongoing_trades else current_time
            }
            
            # logger.debug(f"🕯️ Ongoing {interval} candle: O=${open_price:.2f} H=${high_price:.2f} L=${low_price:.2f} C=${close_price:.2f} V={volume:.2f} ({len(ongoing_trades)} trades)")
            return ongoing_candle
            
        except Exception as e:
            logger.error(f"Failed to get ongoing candle for {symbol}: {e}")
            return None

    def _get_interval_seconds(self, interval: str) -> int:
        """Convert interval string to seconds"""
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400
        }
        return interval_map.get(interval, 300)  # Default to 5m

    # get_volume_analysis() REMOVED - Volume logic moved to VolumeCalculator for clean architecture
    # MarketDataManager now handles volume analysis using VolumeCalculator delegation

    # get_volatility_analysis() removed - using 5m candle volatility instead of orderbook volatility

    # get_pressure() REMOVED - Pressure logic moved to PressureCalculator for clean architecture
    # MarketDataManager now handles pressure analysis using PressureCalculator delegation

    def get_historical_candles(self, symbol: str = None, interval: str = "1m", limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical candle data from Hyperliquid API
        
        Args:
            symbol: Trading symbol (default: BTC)
            interval: Candle interval (1m, 5m, 1h, 1d)
            limit: Number of candles to retrieve
            
        Returns:
            List of candle dictionaries with OHLCV data
        """
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Hyperliquid API endpoint for historical data
            url = f"{self.base_url}/info"
            
            # Calculate time range based on interval
            if interval == "1d":
                # For daily candles, use calendar-based dates, not rolling windows
                from datetime import datetime, timedelta
                now = datetime.now()
                # Use start of today as end time to get completed daily candles
                end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                start_time = end_time - timedelta(days=limit-1)  # Go back (limit-1) days
                
                start_timestamp = int(start_time.timestamp() * 1000)
                end_timestamp = int(end_time.timestamp() * 1000)
            else:
                # For intraday candles, use rolling window approach
                interval_minutes = {
                    "1m": 1,
                    "5m": 5,
                    "1h": 60
                }.get(interval, 1)
                
                start_timestamp = int((time.time() - (limit * interval_minutes * 60)) * 1000)
                end_timestamp = int(time.time() * 1000)
            
            # Request payload for historical candles
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": symbol,
                    "interval": interval,
                    "startTime": start_timestamp,
                    "endTime": end_timestamp
                }
            }
            
            if interval == "1d":
                logger.info(f"🕯️ Requesting {limit} {interval} candles for {symbol} (calendar-based dates)")
            else:
                logger.info(f"🕯️ Requesting {limit} {interval} candles for {symbol} (rolling window approach)")
            logger.debug(f"🕯️ Payload: {payload}")
            
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"🕯️ Hyperliquid API response: {len(data) if isinstance(data, list) else 'not a list'}")
            # Hyperliquid returns candles directly as a list
            if isinstance(data, list) and len(data) > 0:
                candles = data
                
                # Convert to our format and take the last 'limit' candles
                formatted_candles = []
                for candle in candles[-limit:]:
                    formatted_candle = {
                        "open": float(candle.get("o", "0")),
                        "high": float(candle.get("h", "0")),
                        "low": float(candle.get("l", "0")),
                        "close": float(candle.get("c", "0")),
                        "volume": float(candle.get("v", "0")),
                        "timestamp": int(candle.get("t", time.time() * 1000)) // 1000  # Convert ms to seconds
                    }
                    formatted_candles.append(formatted_candle)
                
                logger.debug(f"📊 Fetched {len(formatted_candles)} candles from Hyperliquid for {symbol}")
                return formatted_candles
            else:
                logger.warning(f"⚠️ No candles data in Hyperliquid response: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch Hyperliquid candles: {e}")
            return None

    def get_funding_rate(self, symbol: str = None) -> Dict[str, Any]:
        """Get current funding rate for a symbol"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "meta",
                "coin": symbol
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract funding rate from meta data
            if data and 'fundingRate' in data:
                funding_rate = float(data['fundingRate'])
                return {
                    "funding_rate": funding_rate,
                    "funding_rate_percentage": funding_rate * 100,
                    "next_funding_time": data.get('nextFundingTime', 0),
                    "symbol": symbol,
                    "timestamp": time.time(),
                    "data_source": "hyperliquid_api"
                }
            else:
                # Fallback: calculate funding rate from mark/index price difference
                market_data = self.get_market_data(symbol)
                if market_data and 'markPrice' in market_data and 'indexPrice' in market_data:
                    mark_price = float(market_data['markPrice'])
                    index_price = float(market_data['indexPrice'])
                    
                    # Calculate funding rate based on price difference
                    price_diff = (mark_price - index_price) / index_price
                    funding_rate = price_diff * 0.0001  # 0.01% per hour base rate
                    
                    # Clamp to reasonable range
                    funding_rate = max(-0.0075, min(0.0075, funding_rate))  # ±0.75% per hour max
                    
                    return {
                        "funding_rate": funding_rate,
                        "funding_rate_percentage": funding_rate * 100,
                        "mark_price": mark_price,
                        "index_price": index_price,
                        "price_difference": price_diff,
                        "symbol": symbol,
                        "timestamp": time.time(),
                        "data_source": "calculated_fallback"
                    }
                else:
                    return {
                        "funding_rate": 0.0,
                        "funding_rate_percentage": 0.0,
                        "symbol": symbol,
                        "timestamp": time.time(),
                        "data_source": "default_fallback",
                        "error": "No funding rate data available"
                    }
            
        except Exception as e:
            logger.error(f"❌ Failed to get funding rate for {symbol}: {e}")
            return {
                "funding_rate": 0.0,
                "funding_rate_percentage": 0.0,
                "symbol": symbol,
                "timestamp": time.time(),
                "data_source": "error_fallback",
                "error": str(e)
            }

    # ==================================================================================
    # ALL TRADING METHODS REMOVED - HyperliquidSimulator handles all trading operations
    # Methods eliminated: get_account_info, get_account_balance, get_open_positions, 
    # get_open_orders, get_mark_price, set_leverage, get_leverage, place_order,
    # place_market_order, place_limit_order, cancel_order, get_positions, 
    # get_trade_history, calculate_liquidation_price, 
    # _sign_order, _create_signed_order_payload
    # (540 lines of dead trading code eliminated)
    # ==================================================================================

# Global instance to avoid multiple authentication calls
_global_hyperliquid_api = None

def get_hyperliquid_api() -> HyperliquidAPI:
    """Get the global HyperliquidAPI instance (singleton pattern)"""
    global _global_hyperliquid_api
    if _global_hyperliquid_api is None:
        _global_hyperliquid_api = HyperliquidAPI()
        logger.info("🔌 Created global HyperliquidAPI instance")
    return _global_hyperliquid_api
