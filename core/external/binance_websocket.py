#!/usr/bin/env python3
"""
Binance WebSocket Real-Time Volume Streamer
Provides real-time volume data from individual trades for scalping
"""

import asyncio
import json
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from loguru import logger
import websockets
from collections import deque

class BinanceWebSocket:
    """Real-time volume streaming via Binance WebSocket"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.connected = False
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Volume tracking
        self.volume_cache = {
            "current_volume_btc": 0.0,
            "current_volume_usd": 0.0,
            "volume_per_minute": 0.0,
            "volume_per_second": 0.0,
            "trade_count_per_minute": 0,
            "trade_count_per_second": 0,
            "volume_spike_detected": False,
            "volume_ratio": 1.0,
            "timestamp": 0.0,
            "source": "binance_websocket",
            "connection_status": "disconnected"
        }
        
        # Trade history for volume calculation
        self.trade_history = deque(maxlen=3600)  # Keep 1 hour of trades
        self.volume_history = deque(maxlen=300)  # Keep 5 minutes of volume data
        
        # Thread safety
        self._lock = threading.RLock()
        self._volume_callbacks = []
        
        # WebSocket connection
        self.websocket = None
        self.ws_thread = None
        
        logger.info(f"🔌 Binance WebSocket initialized for {symbol}")
    
    def add_volume_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback function to be called on volume updates"""
        self._volume_callbacks.append(callback)
        logger.debug(f"📞 Added volume callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def get_volume_data(self) -> Dict[str, Any]:
        """Get current volume data from cache (thread-safe)"""
        with self._lock:
            return self.volume_cache.copy()
    
    def start(self):
        """Start WebSocket connection"""
        if self.running:
            logger.warning("WebSocket already running")
            return
        
        self.running = True
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        logger.info("🚀 Binance WebSocket started")
    
    def stop(self):
        """Stop WebSocket connection"""
        self.running = False
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
        logger.info("🛑 Binance WebSocket stopped")
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connected and self.running
    
    def _run_websocket(self):
        """Run WebSocket in separate thread"""
        try:
            asyncio.run(self._websocket_loop())
        except Exception as e:
            logger.error(f"❌ WebSocket thread error: {e}")
    
    async def _websocket_loop(self):
        """Main WebSocket connection loop"""
        while self.running:
            try:
                # Create stream URL for trade data
                stream_name = f"{self.symbol.lower()}@trade"
                ws_url = f"{self.ws_url}/{stream_name}"
                
                logger.info(f"🔌 Connecting to Binance WebSocket: {ws_url}")
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    self.reconnect_attempts = 0
                    
                    with self._lock:
                        self.volume_cache["connection_status"] = "connected"
                    
                    logger.success("✅ Binance WebSocket connected successfully")
                    
                    # Listen for trade messages
                    async for message in websocket:
                        if not self.running:
                            break
                        await self._process_trade_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ Binance WebSocket connection closed")
            except Exception as e:
                logger.error(f"❌ Binance WebSocket error: {e}")
            
            # Reconnection logic
            if self.running:
                await self._handle_reconnection()
    
    async def _handle_reconnection(self):
        """Handle WebSocket reconnection"""
        self.connected = False
        with self._lock:
            self.volume_cache["connection_status"] = "reconnecting"
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * self.reconnect_attempts
            logger.info(f"🔄 Reconnecting in {delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            await asyncio.sleep(delay)
        else:
            logger.error("❌ Max reconnection attempts reached")
            self.running = False
    
    async def _process_trade_message(self, message: str):
        """Process individual trade message"""
        try:
            trade_data = json.loads(message)
            
            # Extract trade information
            trade_volume = float(trade_data['q']) if 'q' in trade_data else 0.0  # Volume in BTC
            trade_price = float(trade_data['p']) if 'p' in trade_data else 0.0   # Price in USDT
            trade_time = int(trade_data['T']) if 'T' in trade_data else 0      # Trade time
            is_buyer_maker = trade_data['m'] if 'm' in trade_data else False   # Is buyer maker
            
            # Calculate USD volume
            trade_volume_usd = trade_volume * trade_price
            
            # Store trade in history
            trade_entry = {
                'volume_btc': trade_volume,
                'volume_usd': trade_volume_usd,
                'price': trade_price,
                'timestamp': trade_time / 1000,  # Convert to seconds
                'is_buyer_maker': is_buyer_maker
            }
            
            with self._lock:
                self.trade_history.append(trade_entry)
            
            # Update volume calculations
            self._update_volume_calculations()
            
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"❌ Error processing trade message: {e}")
    
    def _update_volume_calculations(self):
        """Update volume calculations from trade history"""
        try:
            current_time = time.time()
            
            # Calculate volume for different timeframes
            volume_1s = self._calculate_volume_for_period(current_time - 1, current_time)
            volume_1m = self._calculate_volume_for_period(current_time - 60, current_time)
            volume_5m = self._calculate_volume_for_period(current_time - 300, current_time)
            
            # Calculate trade counts
            trades_1s = self._count_trades_for_period(current_time - 1, current_time)
            trades_1m = self._count_trades_for_period(current_time - 60, current_time)
            
            # Detect volume spikes
            volume_spike_detected, volume_ratio = self._detect_volume_spike(volume_1m)
            
            # Update volume cache
            with self._lock:
                self.volume_cache.update({
                    "current_volume_btc": volume_1m,
                    "current_volume_usd": volume_1m * self._get_current_price(),
                    "volume_per_minute": volume_1m,
                    "volume_per_second": volume_1s,
                    "trade_count_per_minute": trades_1m,
                    "trade_count_per_second": trades_1s,
                    "volume_spike_detected": volume_spike_detected,
                    "volume_ratio": volume_ratio,
                    "timestamp": current_time,
                    "source": "binance_websocket"
                })
            
            # Store volume history
            self.volume_history.append({
                'volume_btc': volume_1m,
                'volume_usd': volume_1m * self._get_current_price(),
                'timestamp': current_time
            })
            
            # Call volume callbacks
            for callback in self._volume_callbacks:
                try:
                    callback(self.volume_cache.copy())
                except Exception as e:
                    logger.error(f"❌ Error in volume callback: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error updating volume calculations: {e}")
    
    def _calculate_volume_for_period(self, start_time: float, end_time: float) -> float:
        """Calculate total volume for a time period"""
        total_volume = 0.0
        
        with self._lock:
            for trade in self.trade_history:
                if start_time <= trade['timestamp'] <= end_time:
                    total_volume += trade['volume_btc']
        
        return total_volume
    
    def _count_trades_for_period(self, start_time: float, end_time: float) -> int:
        """Count trades for a time period"""
        trade_count = 0
        
        with self._lock:
            for trade in self.trade_history:
                if start_time <= trade['timestamp'] <= end_time:
                    trade_count += 1
        
        return trade_count
    
    def _detect_volume_spike(self, current_volume: float) -> tuple[bool, float]:
        """Detect volume spikes by comparing with historical average"""
        try:
            if len(self.volume_history) < 5:
                return False, 1.0
            
            # Calculate average volume from last 5 minutes
            recent_volumes = [entry['volume_btc'] for entry in list(self.volume_history)[-5:]]
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            
            if avg_volume == 0:
                return False, 1.0
            
            volume_ratio = current_volume / avg_volume
            volume_spike = volume_ratio > 2.0  # 2x normal volume
            
            return volume_spike, volume_ratio
            
        except Exception as e:
            logger.error(f"❌ Error detecting volume spike: {e}")
            return False, 1.0
    
    def _get_current_price(self) -> float:
        """Get current price from latest trade"""
        try:
            with self._lock:
                if self.trade_history:
                    return self.trade_history[-1]['price']
            return 50000.0  # Fallback price
        except Exception:
            return 50000.0  # Fallback price


# Global instance management
_websocket_instances = {}

def get_binance_websocket(symbol: str = "BTCUSDT") -> BinanceWebSocket:
    """Get or create Binance WebSocket instance"""
    if symbol not in _websocket_instances:
        _websocket_instances[symbol] = BinanceWebSocket(symbol)
    return _websocket_instances[symbol]

def start_binance_websocket(symbol: str = "BTCUSDT"):
    """Start Binance WebSocket for symbol"""
    websocket = get_binance_websocket(symbol)
    if not websocket.is_connected():
        websocket.start()
    return websocket

def stop_binance_websocket(symbol: str = "BTCUSDT"):
    """Stop Binance WebSocket for symbol"""
    if symbol in _websocket_instances:
        _websocket_instances[symbol].stop()
