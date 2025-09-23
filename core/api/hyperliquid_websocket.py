#!/usr/bin/env python3
"""
Hyperliquid WebSocket Price Streamer
Provides real-time price updates via WebSocket connection
"""

import asyncio
import json
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from loguru import logger
import websockets
from datetime import datetime

class HyperliquidWebSocket:
    """Real-time price streaming via Hyperliquid WebSocket"""
    
    def __init__(self, symbol: str = "BTC"):
        self.symbol = symbol
        # Based on Hyperliquid documentation - try the correct WebSocket endpoint
        # For now, use the original endpoint and implement HTTP fallback
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.connected = False
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Price cache
        self.price_cache = {
            "current_price": 0.0,
            "bid": 0.0,
            "ask": 0.0,
            "timestamp": 0.0,
            "source": "websocket",
            "last_update": "",
            "connection_status": "disconnected"
        }
        
        # Thread safety
        self._lock = threading.RLock()
        self._price_callbacks = []
        
        # WebSocket connection
        self.websocket = None
        self.ws_thread = None
        
        logger.info(f"🔌 Hyperliquid WebSocket initialized for {symbol}")
    
    def add_price_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback function to be called on price updates"""
        self._price_callbacks.append(callback)
        # logger.debug(f"📞 Added price callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def get_current_price(self) -> Optional[float]:
        """Get current price from cache (thread-safe)"""
        with self._lock:
            if self.price_cache["current_price"] > 0:
                return self.price_cache["current_price"]
            return None
    
    def get_price_data(self) -> Dict[str, Any]:
        """Get complete price data from cache (thread-safe)"""
        with self._lock:
            return self.price_cache.copy()
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connected and self.running
    
    def start(self):
        """Start WebSocket connection in background thread"""
        if self.running:
            logger.warning("⚠️ WebSocket already running")
            return
        
        self.running = True
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        logger.info("🚀 WebSocket thread started")
    
    def stop(self):
        """Stop WebSocket connection"""
        self.running = False
        self.connected = False
        
        if self.websocket:
            asyncio.run(self._close_websocket())
        
        logger.info("🛑 WebSocket stopped")
    
    def _run_websocket(self):
        """Run WebSocket connection in thread"""
        try:
            asyncio.run(self._websocket_loop())
        except Exception as e:
            logger.error(f"❌ WebSocket thread error: {e}")
    
    async def _websocket_loop(self):
        """Main WebSocket connection loop"""
        while self.running:
            try:
                logger.info(f"🔌 Connecting to Hyperliquid WebSocket: {self.ws_url}")
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    self.reconnect_attempts = 0
                    
                    with self._lock:
                        self.price_cache["connection_status"] = "connected"
                    
                    logger.success("✅ WebSocket connected successfully")
                    
                    # Subscribe to L2 orderbook updates
                    await self._subscribe_to_orderbook()
                    
                    # Listen for messages
                    await self._listen_for_messages()
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ WebSocket connection closed")
            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}")
            
            # Reconnection logic
            if self.running:
                await self._handle_reconnection()
    
    async def _subscribe_to_orderbook(self):
        """Subscribe to L2 orderbook updates based on Hyperliquid WebSocket API"""
        try:
            # Use the correct subscription format from Hyperliquid documentation
            # Format: { "method": "subscribe", "subscription": { "type": "trades", "coin": "BTC" } }
            
            # Subscribe to trades for BTC
            trades_subscription = {
                "method": "subscribe",
                "subscription": {
                    "type": "trades",
                    "coin": self.symbol
                }
            }
            
            await self.websocket.send(json.dumps(trades_subscription))
            logger.info(f"📡 Subscribing to trades for {self.symbol}")
            
            # Wait a moment and subscribe to orderbook
            await asyncio.sleep(1)
            
            # Subscribe to orderbook for BTC
            orderbook_subscription = {
                "method": "subscribe", 
                "subscription": {
                    "type": "l2Book",
                    "coin": self.symbol
                }
            }
            
            await self.websocket.send(json.dumps(orderbook_subscription))
            logger.info(f"📡 Subscribing to l2Book for {self.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to orderbook: {e}")
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                
                await self._process_message(message)
                
        except Exception as e:
            logger.error(f"❌ Error listening for messages: {e}")
    
    async def _process_message(self, message: str):
        """Process incoming WebSocket message based on Hyperliquid API format"""
        try:
            data = json.loads(message)
            
            # Handle subscription response
            if "channel" in data and data["channel"] == "subscriptionResponse":
                logger.info(f"✅ Subscription response: {data.get('data', {})}")
                return
            
            # Handle trades data
            if "channel" in data and data["channel"] == "trades" and "data" in data:
                await self._process_trades_update(data["data"])
            # Handle orderbook data  
            elif "channel" in data and data["channel"] == "l2Book" and "data" in data:
                await self._process_orderbook_update(data["data"])
            elif "error" in data:
                logger.error(f"❌ WebSocket error message: {data['error']}")
            else:
                # logger.debug(f"📨 Received message: {data}")
                pass  # Placeholder for future debug logging
                
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    async def _process_trades_update(self, trades_data: Dict[str, Any]):
        """Process trades update and extract latest price"""
        try:
            if isinstance(trades_data, list) and len(trades_data) > 0:
                # Get the latest trade
                latest_trade = trades_data[0]
                if "px" in latest_trade:
                    price = float(latest_trade["px"])
                    
                    # Update price cache
                    with self._lock:
                        self.price_cache.update({
                            "current_price": price,
                            "bid": price,  # Use trade price as approximation
                            "ask": price,  # Use trade price as approximation
                            "timestamp": time.time(),
                            "source": "websocket_trades",
                            "last_update": datetime.now().strftime("%H:%M:%S"),
                            "connection_status": "connected"
                        })
                    
                    # Call price callbacks
                    for callback in self._price_callbacks:
                        try:
                            callback(self.price_cache)
                        except Exception as e:
                            logger.error(f"❌ Error in price callback: {e}")
                    
            
                    
        except Exception as e:
            logger.error(f"❌ Error processing trades update: {e}")
    
    async def _process_orderbook_update(self, orderbook_data: Dict[str, Any]):
        """Process orderbook update and extract price"""
        try:
            if "levels" in orderbook_data and len(orderbook_data["levels"]) >= 2:
                bids = orderbook_data["levels"][0]
                asks = orderbook_data["levels"][1]
                
                if bids and asks:
                    best_bid = float(bids[0]["px"])
                    best_ask = float(asks[0]["px"])
                    mid_price = (best_bid + best_ask) / 2
                    
                    # Update price cache
                    with self._lock:
                        self.price_cache.update({
                            "current_price": mid_price,
                            "bid": best_bid,
                            "ask": best_ask,
                            "timestamp": time.time(),
                            "source": "websocket",
                            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        })
                    
                    # Call price update callbacks
                    self._notify_price_callbacks()
                    
            
                    
        except Exception as e:
            logger.error(f"❌ Error processing orderbook update: {e}")
    
    def _notify_price_callbacks(self):
        """Notify all registered price callbacks"""
        try:
            price_data = self.get_price_data()
            for callback in self._price_callbacks:
                try:
                    callback(price_data)
                except Exception as e:
                    logger.error(f"❌ Price callback error: {e}")
        except Exception as e:
            logger.error(f"❌ Error notifying callbacks: {e}")
    
    async def _handle_reconnection(self):
        """Handle WebSocket reconnection"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * self.reconnect_attempts
            
            with self._lock:
                self.price_cache["connection_status"] = f"reconnecting_{self.reconnect_attempts}"
            
            logger.warning(f"🔄 Reconnecting in {delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            await asyncio.sleep(delay)
        else:
            logger.error(f"❌ Max reconnection attempts reached ({self.max_reconnect_attempts})")
            with self._lock:
                self.price_cache["connection_status"] = "failed"
            self.running = False
    
    async def _close_websocket(self):
        """Close WebSocket connection"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
        except Exception as e:
            logger.error(f"❌ Error closing WebSocket: {e}")


# Global WebSocket instance
_websocket_instance = None

def get_websocket_instance(symbol: str = "BTC") -> HyperliquidWebSocket:
    """Get or create global WebSocket instance"""
    global _websocket_instance
    if _websocket_instance is None:
        _websocket_instance = HyperliquidWebSocket(symbol)
    return _websocket_instance

def start_websocket(symbol: str = "BTC"):
    """Start global WebSocket instance"""
    ws = get_websocket_instance(symbol)
    ws.start()
    return ws

def stop_websocket():
    """Stop global WebSocket instance"""
    global _websocket_instance
    if _websocket_instance:
        _websocket_instance.stop()
        _websocket_instance = None
