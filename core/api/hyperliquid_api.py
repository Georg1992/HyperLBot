import requests
import json
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from config.config import TradingConfig

# Import analysis modules
import statistics # Added for enhanced volatility analysis
# OrderbookDataFetcher removed - functionality moved to dedicated calculators

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
        
        if self.wallet_address and self.wallet_private_key:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Hyperliquid API using wallet"""
        try:
            # For wallet-based authentication, we use the wallet address directly
            # No additional headers needed for basic info requests
            logger.info("Using wallet-based authentication")
            logger.info(f"Wallet address: {self.wallet_address}")
            
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
                    
                    logger.debug(f"Current {symbol} price: ${mid_price:,.2f} (Bid: ${best_bid:,.2f}, Ask: ${best_ask:,.2f})")
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
            logger.debug(f"Retrieved market data for {symbol}")
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

    # get_volume_analysis() REMOVED - Volume logic moved to VolumeCalculator for clean architecture
    # MarketDataManager now handles volume analysis using VolumeCalculator delegation

    # get_volatility_analysis() removed - using 5m candle volatility instead of orderbook volatility

    # get_pressure() REMOVED - Pressure logic moved to PressureCalculator for clean architecture
    # MarketDataManager now handles pressure analysis using PressureCalculator delegation

    # ==================================================================================
    # ALL TRADING METHODS REMOVED - HyperliquidSimulator handles all trading operations
    # Methods eliminated: get_account_info, get_account_balance, get_open_positions, 
    # get_open_orders, get_mark_price, set_leverage, get_leverage, place_order,
    # place_market_order, place_limit_order, cancel_order, get_positions, 
    # get_trade_history, get_funding_rate, calculate_liquidation_price, 
    # _sign_order, _create_signed_order_payload
    # (540 lines of dead trading code eliminated)
    # ==================================================================================