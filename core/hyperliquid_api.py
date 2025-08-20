import requests
import json
import time
import hmac
import hashlib
import eth_account
from typing import Dict, Any, Optional, List
from loguru import logger
from config import config

class HyperliquidAPI:
    """Hyperliquid API client for trading operations"""
    
    def __init__(self, wallet_address: str = None, wallet_private_key: str = None):
        self.wallet_address = wallet_address or config.WALLET_ADDRESS
        self.wallet_private_key = wallet_private_key or config.WALLET_PRIVATE_KEY
        self.base_url = config.HYPERLIQUID_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HyperliquidTradingBot/1.0'
        })
        
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
    
    def _sign_order(self, order_data: Dict[str, Any]) -> str:
        """Sign order data with private key"""
        try:
            # Create account from private key
            account = eth_account.Account.from_key(self.wallet_private_key)
            
            # Convert order data to canonical JSON string
            order_json = json.dumps(order_data, separators=(',', ':'), sort_keys=True)
            
            # Create message hash
            message_hash = hashlib.sha256(order_json.encode('utf-8')).hexdigest()
            
            # Sign the hash using unsafe_sign_hash
            signed_message = account.unsafe_sign_hash(message_hash)
            
            # Return the signature
            return signed_message.signature.hex()
            
        except Exception as e:
            logger.error(f"Failed to sign order: {e}")
            raise
    
    def _create_signed_order_payload(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a signed order payload"""
        try:
            # Add timestamp and user to order data
            order_data_with_meta = {
                **order_data,
                "timestamp": int(time.time() * 1000),
                "user": self.wallet_address
            }
            
            # Sign the order
            signature = self._sign_order(order_data_with_meta)
            
            # Create final payload with signature
            signed_payload = {
                **order_data_with_meta,
                "signature": signature
            }
            
            return signed_payload
            
        except Exception as e:
            logger.error(f"Failed to create signed order payload: {e}")
            raise
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information and balances"""
        try:
            endpoint = "/info"
            payload = {
                "type": "clearinghouseState",
                "user": self.wallet_address
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully retrieved account info")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise
    
    def get_market_data(self, symbol: str = None) -> Dict[str, Any]:
        """Get current market data for a symbol"""
        try:
            symbol = symbol or config.SYMBOL
            endpoint = "/info"
            payload = {
                "type": "l2Book",
                "coin": symbol
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully retrieved market data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            raise
    
    def get_mark_price(self, symbol: str = None) -> Dict[str, Any]:
        """Get mark price for a symbol"""
        try:
            symbol = symbol or config.SYMBOL
            endpoint = "/info"
            payload = {
                "type": "meta",
                "coin": symbol
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully retrieved mark price for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get mark price: {e}")
            raise
    
    def get_orderbook(self, symbol: str = None) -> Dict[str, Any]:
        """Get order book for a symbol"""
        try:
            symbol = symbol or config.SYMBOL
            endpoint = "/info"
            payload = {
                "type": "orderBook",
                "coin": symbol
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"Failed to get orderbook: {e}")
            raise
    
    def set_leverage(self, symbol: str = None, leverage: int = None) -> Dict[str, Any]:
        """Set leverage for a symbol"""
        try:
            symbol = symbol or config.SYMBOL
            leverage = leverage or config.LEVERAGE
            
            endpoint = "/exchange"
            payload = {
                "type": "setLeverage",
                "coin": symbol,
                "leverage": leverage
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully set leverage to {leverage}x for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            raise
    
    def get_leverage(self, symbol: str = None) -> Dict[str, Any]:
        """Get current leverage for a symbol"""
        try:
            symbol = symbol or config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "userState",
                "user": self.wallet_address
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract leverage info for the specific symbol
            leverage_info = {}
            if 'assetPositions' in data:
                for position in data['assetPositions']:
                    if position.get('coin') == symbol:
                        leverage_info = {
                            'symbol': symbol,
                            'leverage': position.get('leverage', 1),
                            'position_size': position.get('size', 0),
                            'entry_price': position.get('entryPrice', 0)
                        }
                        break
            
            return leverage_info
            
        except Exception as e:
            logger.error(f"Failed to get leverage: {e}")
            raise
    
    def place_order(self, 
                   side: str, 
                   size: float, 
                   price: float = None, 
                   symbol: str = None,
                   order_type: str = "LIMIT",
                   leverage: int = None) -> Dict[str, Any]:
        """Place a new order with leverage"""
        try:
            symbol = symbol or config.SYMBOL
            leverage = leverage or config.LEVERAGE
            
            # Create base order data
            order_data = {
                "type": "order",
                "coin": symbol,
                "side": side.upper(),
                "size": str(size),
                "orderType": order_type.upper()
            }
            
            # Add price for limit orders
            if price and order_type.upper() == "LIMIT":
                order_data["price"] = str(price)
            
            # Add leverage if specified
            if leverage and leverage > 1:
                order_data["leverage"] = leverage
            
            # Create signed payload
            signed_payload = self._create_signed_order_payload(order_data)
            
            logger.info(f"Placing signed order: {json.dumps(signed_payload, indent=2)}")
            
            endpoint = "/exchange"
            response = self.session.post(f"{self.base_url}{endpoint}", json=signed_payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully placed {side} order for {size} {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def place_market_order(self, 
                          side: str, 
                          size: float, 
                          symbol: str = None,
                          leverage: int = None) -> Dict[str, Any]:
        """Place a market order with leverage"""
        return self.place_order(
            side=side,
            size=size,
            symbol=symbol,
            order_type="MARKET",
            leverage=leverage
        )
    
    def place_limit_order(self, 
                         side: str, 
                         size: float, 
                         price: float,
                         symbol: str = None,
                         leverage: int = None) -> Dict[str, Any]:
        """Place a limit order with leverage"""
        return self.place_order(
            side=side,
            size=size,
            price=price,
            symbol=symbol,
            order_type="LIMIT",
            leverage=leverage
        )
    
    def cancel_order(self, order_id: str, symbol: str = None) -> Dict[str, Any]:
        """Cancel an existing order"""
        try:
            symbol = symbol or config.SYMBOL
            
            cancel_data = {
                "type": "cancel",
                "coin": symbol,
                "oid": order_id
            }
            
            endpoint = "/exchange"
            response = self.session.post(f"{self.base_url}{endpoint}", json=cancel_data)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully cancelled order {order_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise
    
    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open orders"""
        try:
            symbol = symbol or config.SYMBOL
            
            # Get user state which includes open orders
            account_info = self.get_account_info()
            
            # Extract open orders from account info
            open_orders = []
            if 'openOrders' in account_info:
                for order in account_info['openOrders']:
                    if order.get('coin') == symbol:
                        open_orders.append(order)
            
            logger.info(f"Retrieved {len(open_orders)} open orders for {symbol}")
            return open_orders
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
    
    def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            symbol = symbol or config.SYMBOL
            
            account_info = self.get_account_info()
            
            positions = []
            if 'assetPositions' in account_info:
                for position in account_info['assetPositions']:
                    if position.get('coin') == symbol:
                        positions.append(position)
            
            logger.info(f"Retrieved {len(positions)} positions for {symbol}")
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history"""
        try:
            symbol = symbol or config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "userFills",
                "user": self.wallet_address,
                "coin": symbol,
                "limit": limit
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved trade history for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            raise
    
    def get_klines(self, symbol: str = None, interval: str = "1m", limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical kline/candlestick data"""
        try:
            symbol = symbol or config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "candleSnapshot",
                "coin": symbol,
                "interval": interval,
                "limit": limit
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved {len(data)} klines for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get klines: {e}")
            raise
    
    def get_funding_rate(self, symbol: str = None) -> Dict[str, Any]:
        """Get current funding rate for a symbol"""
        try:
            symbol = symbol or config.SYMBOL
            
            endpoint = "/info"
            payload = {
                "type": "fundingHistory",
                "coin": symbol,
                "limit": 1
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"Failed to get funding rate: {e}")
            raise
    
    def get_liquidation_price(self, symbol: str = None) -> float:
        """Calculate liquidation price for current position"""
        try:
            symbol = symbol or config.SYMBOL
            
            # Get current position and account info
            positions = self.get_positions(symbol)
            account_info = self.get_account_info()
            
            if not positions:
                return 0.0
            
            position = positions[0]
            position_size = float(position.get('size', 0))
            entry_price = float(position.get('entryPrice', 0))
            leverage = float(position.get('leverage', 1))
            
            if position_size == 0:
                return 0.0
            
            # Calculate liquidation price based on leverage and margin
            margin_ratio = 0.1  # 10% maintenance margin (approximate)
            
            if position_size > 0:  # Long position
                liquidation_price = entry_price * (1 - 1/leverage + margin_ratio)
            else:  # Short position
                liquidation_price = entry_price * (1 + 1/leverage - margin_ratio)
            
            return liquidation_price
            
        except Exception as e:
            logger.error(f"Failed to calculate liquidation price: {e}")
            return 0.0
