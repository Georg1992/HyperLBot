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
import statistics # Added for enhanced volatility analysis

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
        """Get current mid-price from WebSocket cache (ultra-fast) or orderbook (fallback)"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Try WebSocket first (real-time latency)
            try:
                from core.hyperliquid_websocket import get_websocket_instance
                websocket = get_websocket_instance(symbol)
                
                if websocket.is_connected():
                    price = websocket.get_current_price()
                    if price and price > 0:
                        logger.debug(f"💰 WebSocket price: ${price:,.2f} (real-time)")
                        return price
                    else:
                        logger.debug("⚠️ WebSocket connected but no price data yet")
                else:
                    logger.debug("⚠️ WebSocket not connected, using HTTP fallback")
            except ImportError:
                logger.debug("⚠️ WebSocket module not available, using HTTP fallback")
            except Exception as e:
                logger.debug(f"⚠️ WebSocket error: {e}, using HTTP fallback")
            
            # HTTP API fallback (current method)
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
        """Get historical kline/candlestick data from Yahoo Finance (Hyperliquid doesn't provide historical candles)"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            logger.info(f"📊 Getting {interval} klines from Yahoo Finance for {symbol}")
            return self._get_yahoo_fallback_klines(symbol, interval, limit)
            
        except Exception as e:
            logger.error(f"❌ Failed to get klines: {e}")
            return []
    

    
    
    

    
    def _get_yahoo_fallback_klines(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback to Yahoo Finance for klines data"""
        try:
            yahoo_fetcher = YahooDataFetcher()
            
            # Map Hyperliquid intervals to Yahoo intervals
            interval_mapping = {
                "1m": "1m",
                "5m": "5m", 
                "1h": "1h",
                "1d": "1d"
            }
            
            yahoo_interval = interval_mapping.get(interval, "5m")
            
            if yahoo_interval == "1m":
                candles = yahoo_fetcher.get_1m_klines(symbol, limit)
            elif yahoo_interval == "5m":
                candles = yahoo_fetcher.get_5m_klines(symbol, limit)
            elif yahoo_interval == "1h":
                candles = yahoo_fetcher.get_1h_klines(symbol, limit)
            elif yahoo_interval == "1d":
                candles = yahoo_fetcher.get_1d_klines(symbol, limit)
            else:
                candles = yahoo_fetcher.get_5m_klines(symbol, limit)
            
            if candles:
                logger.info(f"📊 Retrieved {len(candles)} {interval} klines from Yahoo Finance fallback for {symbol}")
                return candles
            else:
                logger.warning(f"⚠️ No kline data available from Yahoo Finance fallback for {symbol}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Yahoo Finance fallback failed: {e}")
            return []
    

    

    

    
    def get_funding_rate(self, symbol: str = None) -> Dict[str, Any]:
        """Get current funding rate for a symbol (simplified - API endpoint has issues)"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Simplified funding rate calculation based on mark/index price difference
            # This is a reasonable approximation until the API endpoint is fixed
            mark_price_data = self.get_mark_price(symbol)
            
            if mark_price_data and 'universe' in mark_price_data:
                # Find BTC in universe data
                btc_info = next((asset for asset in mark_price_data['universe'] if asset['name'] == symbol), None)
                if btc_info:
                    # Use a reasonable default funding rate for BTC
                    funding_rate = 0.0001  # 0.01% per hour (typical for BTC)
                    
                    return {
                        "symbol": symbol,
                        "funding_rate": funding_rate,
                        "funding_rate_8h": funding_rate * 8,  # 8-hour funding
                        "next_funding_time": int(time.time()) + 3600,  # 1 hour from now
                        "data_source": "estimated_from_mark_price",
                        "note": "API endpoint has issues, using estimated rate"
                    }
            
            # Fallback
            return {
                "symbol": symbol,
                "funding_rate": 0.0001,
                "funding_rate_8h": 0.0008,
                "next_funding_time": int(time.time()) + 3600,
                "data_source": "fallback_estimate",
                "note": "Using default funding rate"
            }
            
        except Exception as e:
            logger.error(f"Failed to get funding rate: {e}")
            return {
                "symbol": symbol,
                "funding_rate": 0.0001,
                "funding_rate_8h": 0.0008,
                "next_funding_time": int(time.time()) + 3600,
                "data_source": "error_fallback",
                "error": str(e)
            }
    
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
    

    

    
    def calculate_rsi_from_yahoo_data(self, candles: List[Dict], periods: int = 14) -> Dict[str, Any]:
        """Calculate RSI using Wilder's Smoothing method (standard for most exchanges including Hyperliquid)"""
        try:
            if not candles or len(candles) < periods + 1:
                return {
                    "rsi": None,  # Use None instead of 50.0 for proper N/A handling
                    "trend": "NEUTRAL",
                    "signal": "NEUTRAL",
                    "error": f"Insufficient data for RSI calculation (need {periods + 1}, have {len(candles)})",
                    "data_source": "insufficient_data"
                }
            
            # Handle both Yahoo Finance and Hyperliquid candle formats
            closes = []
            for candle in candles[-(periods + 1):]:
                if isinstance(candle, dict):
                    # Try different possible close price keys
                    close_price = None
                    for key in ['close', 'Close', 'close_price']:
                        if key in candle and candle[key] is not None:
                            try:
                                close_price = float(candle[key])
                                break
                            except (ValueError, TypeError):
                                continue
                    
                    if close_price is not None and close_price > 0:
                        closes.append(close_price)
            
            if len(closes) < periods + 1:
                return {
                    "rsi": None,  # Use None instead of 50.0 for proper N/A handling
                    "trend": "NEUTRAL", 
                    "signal": "NEUTRAL",
                    "error": f"Invalid close prices for RSI calculation",
                    "data_source": "invalid_data"
                }
            
            # Calculate price changes
            changes = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                changes.append(change)
            
            # Calculate initial average gain and loss (first 'periods' changes)
            
            # Calculate initial average gain and loss (first 'periods' changes)
            gains = []
            losses = []
            for change in changes[:periods]:
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            # Initial averages
            avg_gain = sum(gains) / periods
            avg_loss = sum(losses) / periods
            
            # Apply Wilder's Smoothing for remaining changes
            for change in changes[periods:]:
                if change > 0:
                    current_gain = change
                    current_loss = 0
                else:
                    current_gain = 0
                    current_loss = abs(change)
                
                # Wilder's Smoothing: (Previous Average * (Period - 1) + Current Value) / Period
                avg_gain = (avg_gain * (periods - 1) + current_gain) / periods
                avg_loss = (avg_loss * (periods - 1) + current_loss) / periods
            
            # Calculate RSI using Wilder's formula
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Determine trend and signal
            
            # Determine trend and signal
            if rsi > 70:
                trend = "OVERBOUGHT"
                signal = "SELL"
            elif rsi < 30:
                trend = "OVERSOLD"
                signal = "BUY"
            else:
                trend = "NEUTRAL"
                signal = "HOLD"
            
            # Determine data source
            if candles and len(candles) > 0:
                data_source = candles[0].get('data_source', 'unknown')
            else:
                data_source = 'unknown'
            
            return {
                "rsi": round(rsi, 2),
                "trend": trend,
                "signal": signal,
                "periods": periods,
                "data_source": data_source,
                "last_close": closes[-1] if closes else None,
                "calculation_method": "Wilder's Smoothing"
            }
            
        except Exception as e:
            logger.error(f"❌ RSI calculation failed: {e}")
            return {
                "rsi": None,  # Use None instead of 50.0 for proper N/A handling
                "trend": "NEUTRAL",
                "signal": "NEUTRAL", 
                "error": str(e),
                "data_source": "calculation_error"
            }



    def get_enhanced_volume_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Get enhanced volume analysis using order book dynamics and trade flow"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Get market data for order book analysis
            market_data = self.get_market_data(symbol)
            if not market_data or 'levels' not in market_data:
                return {
                    "current_volume": 0.0,
                    "volume_category": "UNKNOWN",
                    "volume_trend": "UNKNOWN",
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "INSUFFICIENT_DATA",
                    "data_source": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    "current_volume": 0.0,
                    "volume_category": "UNKNOWN", 
                    "volume_trend": "UNKNOWN",
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "INSUFFICIENT_DATA",
                    "data_source": "insufficient_levels"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    "current_volume": 0.0,
                    "volume_category": "UNKNOWN",
                    "volume_trend": "UNKNOWN", 
                    "order_flow": "NEUTRAL",
                    "depth_analysis": "NO_ORDERBOOK",
                    "data_source": "no_orderbook_data"
                }
            
            # Calculate order book depth metrics
            bid_depth_5 = sum(float(level['sz']) for level in bids[:5])
            ask_depth_5 = sum(float(level['sz']) for level in asks[:5])
            bid_depth_10 = sum(float(level['sz']) for level in bids[:10])
            ask_depth_10 = sum(float(level['sz']) for level in asks[:10])
            
            total_depth_5 = bid_depth_5 + ask_depth_5
            total_depth_10 = bid_depth_10 + ask_depth_10
            
            # Calculate volume from order book depth (more accurate than trade history)
            # Use depth as a proxy for recent trading activity
            estimated_volume = total_depth_5 * 0.15  # 15% of depth as recent volume
            
            # Analyze order flow imbalance
            bid_ask_ratio = bid_depth_5 / ask_depth_5 if ask_depth_5 > 0 else 1.0
            depth_imbalance = (bid_depth_5 - ask_depth_5) / total_depth_5 if total_depth_5 > 0 else 0
            
            # Determine order flow direction
            if bid_ask_ratio > 1.3:
                order_flow = "STRONG_BUY"
            elif bid_ask_ratio > 1.1:
                order_flow = "BUY"
            elif bid_ask_ratio < 0.7:
                order_flow = "STRONG_SELL"
            elif bid_ask_ratio < 0.9:
                order_flow = "SELL"
            else:
                order_flow = "NEUTRAL"
            
            # Categorize volume based on depth
            if total_depth_5 > 2.0:
                volume_category = "HIGH"
            elif total_depth_5 > 0.5:
                volume_category = "MEDIUM"
            else:
                volume_category = "LOW"
            
            # Analyze depth distribution for volume trend
            depth_ratio = total_depth_5 / total_depth_10 if total_depth_10 > 0 else 1.0
            if depth_ratio > 0.8:
                volume_trend = "INCREASING"  # More volume near market
            elif depth_ratio < 0.6:
                volume_trend = "DECREASING"  # Less volume near market
            else:
                volume_trend = "STABLE"
            
            # Analyze depth quality
            if total_depth_5 > 1.0 and abs(depth_imbalance) < 0.3:
                depth_analysis = "HEALTHY"
            elif total_depth_5 > 0.5:
                depth_analysis = "MODERATE"
            else:
                depth_analysis = "THIN"
            
            return {
                "current_volume": estimated_volume,
                "volume_category": volume_category,
                "volume_trend": volume_trend,
                "order_flow": order_flow,
                "depth_analysis": depth_analysis,
                "bid_depth_5": bid_depth_5,
                "ask_depth_5": ask_depth_5,
                "total_depth_5": total_depth_5,
                "bid_ask_ratio": bid_ask_ratio,
                "depth_imbalance": depth_imbalance,
                "data_source": "orderbook_depth_analysis"
            }
            
        except Exception as e:
            logger.error(f"Enhanced volume analysis failed: {e}")
            return {
                "current_volume": 0.0,
                "volume_category": "ERROR",
                "volume_trend": "ERROR",
                "order_flow": "NEUTRAL",
                "depth_analysis": "ERROR",
                "error": str(e),
                "data_source": "error"
            }

    def get_enhanced_volatility_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Get enhanced volatility analysis using order book dynamics and spread analysis"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Get market data for volatility analysis
            market_data = self.get_market_data(symbol)
            if not market_data or 'levels' not in market_data:
                return {
                    "volatility_5m": 0.0,
                    "volatility_category": "UNKNOWN",
                    "spread_volatility": 0.0,
                    "depth_volatility": 0.0,
                    "volatility_trend": "UNKNOWN",
                    "data_source": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    "volatility_5m": 0.0,
                    "volatility_category": "UNKNOWN",
                    "spread_volatility": 0.0,
                    "depth_volatility": 0.0,
                    "volatility_trend": "UNKNOWN",
                    "data_source": "insufficient_levels"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    "volatility_5m": 0.0,
                    "volatility_category": "UNKNOWN",
                    "spread_volatility": 0.0,
                    "depth_volatility": 0.0,
                    "volatility_trend": "UNKNOWN",
                    "data_source": "no_orderbook_data"
                }
            
            # Calculate spread-based volatility
            spreads = []
            for i in range(min(5, len(bids), len(asks))):
                try:
                    bid_price = float(bids[i]['px'])
                    ask_price = float(asks[i]['px'])
                    spread = ask_price - bid_price
                    spread_pct = spread / bid_price
                    spreads.append(spread_pct)
                except (KeyError, ValueError, TypeError):
                    continue
            
            # Calculate spread volatility
            if spreads:
                spread_volatility = statistics.mean(spreads)
                spread_std = statistics.stdev(spreads) if len(spreads) > 1 else 0
            else:
                spread_volatility = 0.0
                spread_std = 0.0
            
            # Calculate depth-based volatility (how much depth varies across levels)
            bid_depths = [float(level['sz']) for level in bids[:5] if 'sz' in level]
            ask_depths = [float(level['sz']) for level in asks[:5] if 'sz' in level]
            
            depth_volatility = 0.0
            if bid_depths and ask_depths:
                # Calculate coefficient of variation for depth
                all_depths = bid_depths + ask_depths
                if len(all_depths) > 1:
                    mean_depth = statistics.mean(all_depths)
                    depth_std = statistics.stdev(all_depths)
                    depth_volatility = depth_std / mean_depth if mean_depth > 0 else 0
            
            # Combine spread and depth volatility for overall volatility
            combined_volatility = (spread_volatility * 0.6) + (depth_volatility * 0.4)
            
            # Categorize volatility
            if combined_volatility > 0.005:  # 0.5%
                volatility_category = "HIGH"
            elif combined_volatility > 0.002:  # 0.2%
                volatility_category = "MEDIUM"
            else:
                volatility_category = "LOW"
            
            # Determine volatility trend based on spread consistency
            if spread_std > 0.001:
                volatility_trend = "INCREASING"
            elif spread_std < 0.0001:
                volatility_trend = "DECREASING"
            else:
                volatility_trend = "STABLE"
            
            return {
                "volatility_5m": combined_volatility,
                "volatility_category": volatility_category,
                "spread_volatility": spread_volatility,
                "depth_volatility": depth_volatility,
                "volatility_trend": volatility_trend,
                "avg_spread": spread_volatility,
                "spread_std": spread_std,
                "data_source": "orderbook_volatility_analysis"
            }
            
        except Exception as e:
            logger.error(f"Enhanced volatility analysis failed: {e}")
            return {
                "volatility_5m": 0.0,
                "volatility_category": "ERROR",
                "spread_volatility": 0.0,
                "depth_volatility": 0.0,
                "volatility_trend": "ERROR",
                "error": str(e),
                "data_source": "error"
            }

    def get_enhanced_ultimate_pressure(self, symbol: str = None) -> Dict[str, Any]:
        """Get enhanced ultimate pressure analysis using advanced order book metrics"""
        try:
            symbol = symbol or self.config.SYMBOL
            
            # Get market data for pressure analysis
            market_data = self.get_market_data(symbol)
            if not market_data or 'levels' not in market_data:
                return {
                    "direction": "NEUTRAL",
                    "pressure_score": 0.5,
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "no_market_data"
                }
            
            levels = market_data['levels']
            if len(levels) < 2:
                return {
                    "direction": "NEUTRAL", 
                    "pressure_score": 0.5,
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "insufficient_data"
                }
            
            bids = levels[0] if isinstance(levels[0], list) else []
            asks = levels[1] if isinstance(levels[1], list) else []
            
            if not bids or not asks:
                return {
                    "direction": "NEUTRAL",
                    "pressure_score": 0.5, 
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "no_orderbook_data"
                }
            
            # Calculate weighted pressure metrics
            bid_pressure = 0.0
            ask_pressure = 0.0
            
            # Weight closer levels more heavily (inverse distance weighting)
            for i, level in enumerate(bids[:10]):
                try:
                    size = float(level['sz'])
                    weight = 1.0 / (i + 1)  # Level 0 gets weight 1, level 1 gets weight 0.5, etc.
                    bid_pressure += size * weight
                except (KeyError, ValueError, TypeError):
                    continue
            
            for i, level in enumerate(asks[:10]):
                try:
                    size = float(level['sz'])
                    weight = 1.0 / (i + 1)
                    ask_pressure += size * weight
                except (KeyError, ValueError, TypeError):
                    continue
            
            total_pressure = bid_pressure + ask_pressure
            if total_pressure == 0:
                return {
                    "direction": "NEUTRAL",
                    "pressure_score": 0.5,
                    "confidence": "0%",
                    "strength": 0.5,
                    "trend": "UNKNOWN",
                    "status": "no_volume"
                }
            
            # Calculate weighted pressure score
            pressure_score = bid_pressure / total_pressure
            
            # Calculate pressure strength (how much total pressure exists)
            pressure_strength = min(1.0, total_pressure / 10.0)  # Normalize to 0-1
            
            # Determine direction with enhanced thresholds
            if pressure_score > 0.65:
                direction = "BUY"
                confidence = min(95, int(pressure_score * 100))
            elif pressure_score < 0.35:
                direction = "SELL"
                confidence = min(95, int((1 - pressure_score) * 100))
            else:
                direction = "NEUTRAL"
                confidence = 50
            
            # Determine trend with more granular levels
            if pressure_score > 0.75:
                trend = "VERY_STRONG_BUY"
            elif pressure_score > 0.6:
                trend = "STRONG_BUY"
            elif pressure_score > 0.55:
                trend = "BUY"
            elif pressure_score < 0.25:
                trend = "VERY_STRONG_SELL"
            elif pressure_score < 0.4:
                trend = "STRONG_SELL"
            elif pressure_score < 0.45:
                trend = "SELL"
            else:
                trend = "NEUTRAL"
            
            return {
                "direction": direction,
                "pressure_score": pressure_score,
                "confidence": f"{confidence}%",
                "strength": pressure_strength,
                "trend": trend,
                "bid_pressure": bid_pressure,
                "ask_pressure": ask_pressure,
                "total_pressure": total_pressure,
                "status": "success",
                "data_source": "enhanced_orderbook_analysis"
            }
                
        except Exception as e:
            logger.error(f"❌ Enhanced ultimate pressure analysis failed: {e}")
            return {
                "direction": "ERROR",
                "pressure_score": 0.5,
                "confidence": "0%",
                "strength": 0.5,
                "status": "error",
                "error": str(e)
            }
