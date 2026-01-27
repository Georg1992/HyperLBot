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
        """
        Authenticate with Hyperliquid API using wallet
        
        CRITICAL FIX #4: Security - Never log wallet addresses or private keys.
        Logging sensitive data is a security vulnerability.
        """
        try:
            # Skip if already authenticated
            if self._authenticated:
                return
                
            # For wallet-based authentication, we use the wallet address directly
            # No additional headers needed for basic info requests
            
            # CRITICAL FIX #4: Never log wallet addresses or private keys
            # Only log that authentication is being attempted (without sensitive data)
            if self.wallet_address:
                # Log only a masked version for debugging (first 6, last 4 chars)
                masked_address = f"{self.wallet_address[:6]}...{self.wallet_address[-4:]}" if len(self.wallet_address) > 10 else "***"
                logger.debug(f"Using wallet-based authentication (address: {masked_address})")
            else:
                logger.debug("Using wallet-based authentication (no wallet address provided)")
            
            # CRITICAL: Never log private key, even in debug mode
            if self.wallet_private_key:
                logger.debug("Private key provided (not logged for security)")
            else:
                logger.debug("No private key provided")
            
            # Mark as authenticated
            self._authenticated = True
            
        except Exception as e:
            # CRITICAL: Don't include sensitive data in error messages
            logger.error(f"Authentication failed: {str(e)}")
            raise

    # ==================================================================================
    # USED METHODS ONLY (6 methods) - All trading methods removed (simulator handles)
    # ==================================================================================

    def get_current_price(self, symbol: str = None) -> Optional[float]:
        """Get current price from WebSocket ONLY - single source of truth"""
        symbol = symbol or self.config.SYMBOL
        
        # WebSocket is the ONLY price source - no fallbacks
        try:
            from core.api.hyperliquid_websocket import get_websocket_instance
            websocket = get_websocket_instance(symbol)
            
            # Ensure WebSocket is started if not already running
            if not websocket.running:
                logger.info(f"🚀 Starting WebSocket for {symbol}")
                websocket.start()
                
                # Wait for WebSocket to connect and receive price data
                import time
                max_wait = 10  # Maximum 10 seconds
                wait_time = 0
                while wait_time < max_wait:
                    if websocket.is_connected():
                        # Check if we have price data
                        price = websocket.get_current_price()
                        if price and price > 0:
                            logger.info(f"✅ WebSocket connected and price data available after {wait_time}s")
                            break
                    time.sleep(0.5)
                    wait_time += 0.5
                
                if wait_time >= max_wait:
                    logger.error(f"❌ WebSocket failed to connect or receive price data within {max_wait}s")
                    return None
            
            if websocket.is_connected():
                price = websocket.get_current_price()
                if price and price > 0:
                    return price
                else:
                    logger.warning(f"⚠️ WebSocket connected but no price data available for {symbol}")
                    return None
            else:
                logger.error(f"❌ WebSocket not connected for {symbol} - price unavailable")
                return None
                
        except ImportError:
            logger.error("❌ WebSocket module not available - price unavailable")
            return None
        except Exception as e:
            logger.error(f"❌ WebSocket error for {symbol}: {e} - price unavailable")
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

    def _get_interval_seconds(self, interval: str) -> int:
        """Convert interval string to seconds"""
        interval_map = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "2h": 7200,
            "4h": 14400,
            "8h": 28800,
            "12h": 43200,
            "1d": 86400,
            "3d": 259200,
            "1w": 604800,
            "1M": 2592000
        }
        return interval_map[interval] if interval in interval_map else 300  # Default to 5m

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
                # Include today's candle by using current time as end time
                end_time = now
                start_time = end_time - timedelta(days=limit-1)  # Go back (limit-1) days
                
                start_timestamp = int(start_time.timestamp() * 1000)
                end_timestamp = int(end_time.timestamp() * 1000)
            else:
                # For intraday candles, use rolling window approach
                interval_minutes = {
                    "1m": 1,
                    "3m": 3,
                    "5m": 5,
                    "15m": 15,
                    "30m": 30,
                    "1h": 60,
                    "2h": 120,
                    "4h": 240,
                    "8h": 480,
                    "12h": 720
                }[interval] if interval in {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400} else 1
                
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
                        "open": float(candle["o"]) if "o" in candle else 0.0,
                        "high": float(candle["h"]) if "h" in candle else 0.0,
                        "low": float(candle["l"]) if "l" in candle else 0.0,
                        "close": float(candle["c"]) if "c" in candle else 0.0,
                        "volume": float(candle["v"]) if "v" in candle else 0.0,
                        "timestamp": int(candle["t"]) // 1000 if "t" in candle else int(time.time())  # Convert ms to seconds
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
                "type": "metaAndAssetCtxs"
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract funding rate from metaAndAssetCtxs data
            if data and isinstance(data, list) and len(data) >= 2:
                universe = data[0]
                asset_contexts = data[1]
                
                if isinstance(universe, dict) and 'universe' in universe:
                    universe_list = universe['universe']
                    
                    # Find the symbol in universe
                    symbol_index = None
                    for i, asset in enumerate(universe_list):
                        if isinstance(asset, dict) and ('name' in asset and asset['name'] == symbol):
                            symbol_index = i
                            break
                    
                    if symbol_index is not None and symbol_index < len(asset_contexts):
                        asset_context = asset_contexts[symbol_index]
                        
                        if isinstance(asset_context, dict) and 'funding' in asset_context:
                            funding_rate_str = asset_context['funding']
                            funding_rate = float(funding_rate_str)
                            
                            return {
                                "funding_rate": funding_rate,
                                "funding_rate_percentage": funding_rate * 100,
                                "next_funding_time": 0,  # Not provided in this endpoint
                                "symbol": symbol,
                                "timestamp": time.time(),
                                "data_source": "hyperliquid_api",
                                "mark_price": float(asset_context['markPx']) if 'markPx' in asset_context else 0.0,
                                "oracle_price": float(asset_context['oraclePx']) if 'oraclePx' in asset_context else 0.0,
                                "open_interest": float(asset_context['openInterest']) if 'openInterest' in asset_context else 0.0
                            }
            
            # NO FALLBACKS - Real funding rate data not available
            raise ValueError("Real funding rate data not available from Hyperliquid API - NO FALLBACKS")
            
        except Exception as e:
            logger.error(f"❌ Failed to get funding rate for {symbol}: {e}")
            raise ValueError(f"Funding rate fetch failed - NO FALLBACKS: {e}")

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
