import requests
import json
import time
import hmac
import hashlib
import eth_account
from typing import Dict, Any, Optional, List
from loguru import logger
from .config import TradingConfig

# Import data modules to avoid lazy import issues
from data.yahoo_data_fetcher import YahooDataFetcher

class HyperliquidAPI:
    """Hyperliquid API client for trading operations"""
    
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
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get real account balance and margin info"""
        try:
            account_info = self.get_account_info()
            
            balance_data = {
                "account_value": 0.0,
                "total_margin_used": 0.0,
                "available_margin": 0.0,
                "total_unrealized_pnl": 0.0,
                "withdrawal_balance": 0.0,
                "timestamp": time.time(),
                "source": "hyperliquid_real"
            }
            
            # Extract balance information from marginSummary
            if account_info and 'marginSummary' in account_info:
                margin = account_info['marginSummary']
                balance_data.update({
                    "account_value": float(margin.get('accountValue', '0')),
                    "total_margin_used": float(margin.get('totalMarginUsed', '0')),
                    "available_margin": float(margin.get('availableMargin', '0')),
                    "total_unrealized_pnl": float(margin.get('totalUnrealizedPnl', '0')),
                    "withdrawal_balance": float(margin.get('withdrawable', '0'))
                })
            
            # Calculate additional metrics
            balance_data["margin_usage_pct"] = (
                (balance_data["total_margin_used"] / balance_data["account_value"] * 100) 
                if balance_data["account_value"] > 0 else 0
            )
            
            logger.info(f"💰 Real Account Balance: ${balance_data['account_value']:.2f}")
            logger.info(f"📊 Available Margin: ${balance_data['available_margin']:.2f}")
            logger.info(f"💹 Unrealized PnL: ${balance_data['total_unrealized_pnl']:.2f}")
            
            return balance_data
            
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            return {
                "account_value": 0.0,
                "total_margin_used": 0.0,
                "available_margin": 0.0,
                "total_unrealized_pnl": 0.0,
                "withdrawal_balance": 0.0,
                "margin_usage_pct": 0.0,
                "timestamp": time.time(),
                "source": "error",
                "error": str(e)
            }
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions from account"""
        try:
            account_info = self.get_account_info()
            
            # Extract positions from clearinghouse state
            positions = []
            if account_info and 'assetPositions' in account_info:
                for position in account_info['assetPositions']:
                    if position.get('position', {}).get('szi', '0') != '0':
                        # Position is open (size != 0)
                        position_data = {
                            "symbol": position.get('position', {}).get('coin', 'UNKNOWN'),
                            "size": float(position.get('position', {}).get('szi', '0')),
                            "entry_price": float(position.get('position', {}).get('entryPx', '0')),
                            "unrealized_pnl": float(position.get('position', {}).get('unrealizedPnl', '0')),
                            "leverage": float(position.get('position', {}).get('leverage', {}).get('value', '1')),
                            "side": "LONG" if float(position.get('position', {}).get('szi', '0')) > 0 else "SHORT",
                            "margin_used": float(position.get('position', {}).get('marginUsed', '0')),
                            "timestamp": time.time(),
                            "source": "hyperliquid_real"
                        }
                        positions.append(position_data)
            
            logger.info(f"🔍 Found {len(positions)} open positions")
            for pos in positions:
                logger.info(f"  - {pos['side']} {abs(pos['size'])} {pos['symbol']} @ ${pos['entry_price']:.2f} (PnL: ${pos['unrealized_pnl']:.2f})")
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get open positions: {e}")
            return []
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders from account"""
        try:
            endpoint = "/info"
            payload = {
                "type": "openOrders",
                "user": self.wallet_address
            }
            
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            orders_data = response.json()
            orders = []
            
            if orders_data:
                for order in orders_data:
                    order_info = {
                        "order_id": order.get('oid', 'unknown'),
                        "symbol": order.get('coin', 'UNKNOWN'),
                        "side": order.get('side', 'UNKNOWN'),
                        "size": float(order.get('sz', '0')),
                        "price": float(order.get('limitPx', '0')),
                        "order_type": "LIMIT" if order.get('limitPx') else "MARKET",
                        "timestamp": order.get('timestamp', time.time()),
                        "source": "hyperliquid_real"
                    }
                    orders.append(order_info)
            
            logger.info(f"🔍 Found {len(orders)} open orders")
            for order in orders:
                logger.info(f"  - {order['side']} {order['size']} {order['symbol']} @ ${order['price']:.2f}")
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    def get_current_price(self, symbol: str = None) -> Optional[float]:
        """Get current mid-price from orderbook"""
        try:
            symbol = symbol or self.config.SYMBOL
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
            logger.info(f"Successfully retrieved market data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            raise
    
    def get_mark_price(self, symbol: str = None) -> Dict[str, Any]:
        """Get mark price for a symbol"""
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
            logger.info(f"Successfully retrieved mark price for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get mark price: {e}")
            raise
    
    def get_orderbook(self, symbol: str = None) -> Dict[str, Any]:
        """Get order book for a symbol (uses l2Book data)"""
        try:
            # Use the working l2Book endpoint (same as get_market_data)
            market_data = self.get_market_data(symbol)
            
            if market_data and 'levels' in market_data:
                # Process into standard orderbook format
                bids = market_data['levels'][0] if len(market_data['levels']) > 0 else []
                asks = market_data['levels'][1] if len(market_data['levels']) > 1 else []
                
                # Calculate running totals and format
                processed_bids = []
                processed_asks = []
                bid_total = 0
                ask_total = 0
                
                for bid in bids[:15]:  # Top 15 levels
                    bid_total += float(bid['sz'])
                    processed_bids.append({
                        'price': float(bid['px']),
                        'size': float(bid['sz']),
                        'total': bid_total
                    })
                
                for ask in asks[:15]:  # Top 15 levels
                    ask_total += float(ask['sz'])
                    processed_asks.append({
                        'price': float(ask['px']),
                        'size': float(ask['sz']),
                        'total': ask_total
                    })
                
                # Calculate spread
                best_bid = float(bids[0]['px']) if bids else 0
                best_ask = float(asks[0]['px']) if asks else 0
                spread = best_ask - best_bid
                spread_pct = (spread / best_ask * 100) if best_ask > 0 else 0
                
                return {
                    "bids": processed_bids,
                    "asks": processed_asks,
                    "spread": spread,
                    "spread_pct": spread_pct,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "timestamp": time.time(),
                    "data_source": "hyperliquid_l2book"
                }
            else:
                return {"error": "No orderbook levels in market data"}
            
        except Exception as e:
            logger.error(f"Failed to get orderbook: {e}")
            return {"error": str(e)}
    
    def set_leverage(self, symbol: str = None, leverage: int = None) -> Dict[str, Any]:
        """Set leverage for a symbol"""
        try:
            symbol = symbol or self.config.SYMBOL
            leverage = leverage or self.config.LEVERAGE
            
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
            symbol = symbol or self.config.SYMBOL
            
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
            symbol = symbol or self.config.SYMBOL
            leverage = leverage or self.config.LEVERAGE
            
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
            symbol = symbol or self.config.SYMBOL
            
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
            symbol = symbol or self.config.SYMBOL
            
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
            symbol = symbol or self.config.SYMBOL
            
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
            symbol = symbol or self.config.SYMBOL
            
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
            symbol = symbol or self.config.SYMBOL
            
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
    
    def get_5m_candles_with_volume(self, symbol: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get 5-minute candlestick data with volume information from Yahoo Finance"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Use Yahoo Finance for volume data since Hyperliquid API doesn't support candlestick volume
            yahoo_fetcher = YahooDataFetcher()
            candles = yahoo_fetcher.get_5m_klines(symbol, limit)
            
            if candles:
                logger.info(f"Retrieved {len(candles)} 5m candles with volume from Yahoo Finance for {symbol}")
                return candles
            else:
                logger.warning(f"No volume data available from Yahoo Finance for {symbol}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get 5m candles with volume: {e}")
            return []
    
    def get_current_5m_volume(self, symbol: str = None) -> Dict[str, Any]:
        """Get current 5-minute volume statistics"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Simplified volume data
            volume_data = {
                "current_volume": 0.0,
                "volume_category": "UNKNOWN",
                "avg_volume": 0.0,
                "volume_trend": "UNKNOWN",
                "data_source": "simplified"
            }
            
            logger.debug(f"Retrieved volume data for {symbol}: {volume_data.get('current_volume', 0):.1f} BTC ({volume_data.get('volume_category', 'UNKNOWN')})")
            return volume_data
            
        except Exception as e:
            logger.error(f"Failed to get current 5m volume: {e}")
            return {
                "current_volume": 0,
                "volume_category": "ERROR",
                "avg_volume": 0,
                "volume_trend": "ERROR",
                "error": str(e),
                "data_source": "simplified"
            }
    

    
    def get_funding_rate(self, symbol: str = None) -> Dict[str, Any]:
        """Get current funding rate for a symbol"""
        try:
            symbol = symbol or self.config.SYMBOL
            
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
            symbol = symbol or self.config.SYMBOL
            
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
    
    def get_volume_stats(self, symbol: str = None) -> Dict[str, Any]:
        """Get current volume statistics and 24h trading data"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Try to get volume data from trade history
            try:
                trades = self.get_trade_history(symbol, limit=100)
                if trades:
                    # Calculate recent volume from trades
                    current_time = time.time() * 1000  # Convert to milliseconds
                    one_hour_ago = current_time - (60 * 60 * 1000)
                    
                    recent_trades = [t for t in trades if t.get('time', 0) > one_hour_ago]
                    hour_volume = sum(float(t.get('size', 0)) for t in recent_trades)
                    hour_trade_count = len(recent_trades)
                    
                    # Estimate 24h volume
                    volume_24h_estimate = hour_volume * 24
                    
                    return {
                        "symbol": symbol,
                        "hour_volume": hour_volume,
                        "hour_trade_count": hour_trade_count,
                        "estimated_24h_volume": volume_24h_estimate,
                        "avg_trade_size": hour_volume / hour_trade_count if hour_trade_count > 0 else 0,
                        "data_source": "trade_history_calculation"
                    }
            except Exception as e:
                logger.warning(f"Could not calculate volume from trades: {e}")
            
            # Fallback: Try to get from orderbook depth
            try:
                market_data = self.get_market_data(symbol)
                if market_data and 'levels' in market_data:
                    bids = market_data['levels'][0] if len(market_data['levels']) > 0 else []
                    asks = market_data['levels'][1] if len(market_data['levels']) > 1 else []
                    
                    # Calculate orderbook depth as proxy for volume activity
                    bid_depth = sum(float(level['sz']) for level in bids[:10]) if bids else 0
                    ask_depth = sum(float(level['sz']) for level in asks[:10]) if asks else 0
                    total_depth = bid_depth + ask_depth
                    
                    return {
                        "symbol": symbol,
                        "orderbook_depth": total_depth,
                        "bid_depth": bid_depth,
                        "ask_depth": ask_depth,
                        "depth_imbalance": (bid_depth - ask_depth) / (bid_depth + ask_depth) if total_depth > 0 else 0,
                        "data_source": "orderbook_depth"
                    }
            except Exception as e:
                logger.warning(f"Could not get orderbook depth: {e}")
            
            return {
                "symbol": symbol,
                "error": "No volume data available from Hyperliquid",
                "data_source": "none"
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume stats: {e}")
            return {"error": str(e), "data_source": "error"}
    
    def get_current_market_indicators(self, symbol: str = None) -> Dict[str, Any]:
        """Get comprehensive current market indicators including volume and liquidity metrics"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Get current price from allMids
            endpoint = "/info"
            payload = {"type": "allMids"}
            response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            current_price = 0
            
            if response.status_code == 200:
                mids_data = response.json()
                current_price = float(mids_data.get(symbol, 0))
            
            # Get volume stats
            volume_stats = self.get_volume_stats(symbol)
            
            # Get orderbook for liquidity analysis
            market_data = self.get_market_data(symbol)
            liquidity_metrics = {}
            
            if market_data and 'levels' in market_data and isinstance(market_data['levels'], list) and len(market_data['levels']) >= 2:
                bids_level = market_data['levels'][0]
                asks_level = market_data['levels'][1]
                
                # Ensure bids and asks are lists
                if isinstance(bids_level, list) and isinstance(asks_level, list):
                    bid_depth = 0
                    ask_depth = 0
                    
                    # Calculate bid depth
                    for level in bids_level[:10]:
                        if isinstance(level, dict) and 'sz' in level:
                            bid_depth += float(level['sz'])
                    
                    # Calculate ask depth
                    for level in asks_level[:10]:
                        if isinstance(level, dict) and 'sz' in level:
                            ask_depth += float(level['sz'])
                    
                    total_depth = bid_depth + ask_depth
                    
                    # Calculate spread safely
                    spread = 0
                    spread_pct = 0
                    if bids_level and asks_level:
                        try:
                            best_bid = float(bids_level[0]['px']) if isinstance(bids_level[0], dict) and 'px' in bids_level[0] else 0
                            best_ask = float(asks_level[0]['px']) if isinstance(asks_level[0], dict) and 'px' in asks_level[0] else 0
                            spread = best_ask - best_bid
                            spread_pct = (spread / current_price * 100) if current_price > 0 else 0
                        except (KeyError, ValueError, TypeError):
                            spread = 0
                            spread_pct = 0
                    
                    liquidity_metrics = {
                        "bid_depth": bid_depth,
                        "ask_depth": ask_depth,
                        "total_depth": total_depth,
                        "depth_imbalance": (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0,
                        "spread": spread,
                        "spread_pct": spread_pct
                    }
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "volume_stats": volume_stats,
                "liquidity_metrics": liquidity_metrics,
                "timestamp": time.time(),
                "data_source": "hyperliquid_real_time"
            }
            
        except Exception as e:
            logger.error(f"Failed to get market indicators: {e}")
            return {"error": str(e)}
    
    def calculate_rsi_from_yahoo_data(self, candles: List[Dict], periods: int = 20) -> Dict[str, Any]:
        """Calculate proper RSI using historical price data from Yahoo Finance (20-period for crypto accuracy)"""
        try:
            if not candles or len(candles) < periods + 1:
                return {
                    "rsi": 50.0,
                    "error": f"Insufficient data for RSI calculation (need {periods + 1}, have {len(candles)})",
                    "calculation_method": "insufficient_data"
                }
            
            # Get closing prices
            closes = [float(candle["close"]) for candle in candles[-(periods + 1):]]
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                price_changes.append(change)
            
            # Separate gains and losses
            gains = [change if change > 0 else 0 for change in price_changes]
            losses = [-change if change < 0 else 0 for change in price_changes]
            
            # Calculate average gain and loss
            avg_gain = sum(gains) / periods if gains else 0
            avg_loss = sum(losses) / periods if losses else 0
            
            # Calculate RSI
            if avg_loss == 0:
                rsi = 100.0  # No losses = maximum RSI
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Get current price
            current_price = closes[-1]
            
            return {
                "rsi": rsi,
                "current_price": current_price,
                "calculation_method": f"proper_rsi_{periods}_period",
                "periods_used": periods,
                "avg_gain": avg_gain,
                "avg_loss": avg_loss,
                "overbought_threshold": 70,
                "oversold_threshold": 30,
                "is_overbought": rsi > 70,
                "is_oversold": rsi < 30,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate RSI from Yahoo data: {e}")
            return {"error": str(e), "rsi": 50.0}

    def get_ultimate_pressure(self, symbol: str = None) -> Dict[str, Any]:
        """Get ultimate buy/sell pressure indicator (simplified)"""
        try:
            # Simplified pressure indicator
            return {
                "direction": "NEUTRAL",
                "pressure_score": 0.5,
                "confidence": "50%",
                "trend": "UNKNOWN",
                "active_signals": 0,
                "signal_details": {},
                "status": "success",
                "display": "Simplified pressure indicator"
            }
                
        except Exception as e:
            logger.error(f"❌ Ultimate pressure analysis failed: {e}")
            return {
                "direction": "ERROR",
                "pressure_score": 0,
                "confidence": "0%",
                "status": "error",
                "error": str(e)
            }
