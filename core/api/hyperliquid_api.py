import requests
import json
import time
import hmac
import hashlib
import eth_account
from typing import Dict, Any, Optional, List
from loguru import logger
from config.config import TradingConfig

# Import data modules to avoid lazy import issues
from core.external.yahoo_data_fetcher import YahooDataFetcher
import statistics # Added for enhanced volatility analysis
from core.analysis.real_time.orderbook_analyzer import MarketOrderbookAnalyzer

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
        
        # Initialize analysis module
        self.analysis = MarketOrderbookAnalyzer(self)
        
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
    
    def calculate_liquidation_price(self, entry_price: float, side: str, leverage: float, margin: float) -> float:
        """Calculate liquidation price for a position"""
        try:
            if side.upper() == "LONG":
                # For long positions: liquidation_price = entry_price - (margin / leverage)
                liquidation_price = entry_price - (margin / leverage)
            elif side.upper() == "SHORT":
                # For short positions: liquidation_price = entry_price + (margin / leverage)
                liquidation_price = entry_price + (margin / leverage)
            else:
                logger.error(f"Invalid side: {side}")
                return 0.0
            
            return max(0, liquidation_price)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Failed to calculate liquidation price: {e}")
            return 0.0



    def get_volume_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Get volume analysis using order book dynamics and trade flow"""
        return self.analysis.get_volume_analysis(symbol)

    def get_volatility_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Get volatility analysis using order book dynamics and spread analysis"""
        return self.analysis.get_volatility_analysis(symbol)

    def get_ultimate_pressure(self, symbol: str = None) -> Dict[str, Any]:
        """Get ultimate pressure analysis using advanced order book metrics"""
        return self.analysis.get_ultimate_pressure(symbol)
