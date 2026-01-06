#!/usr/bin/env python3
"""
Binance API Client
Provides real-time volume data via WebSocket for scalping strategies
Also provides historical candle data for initial database population
"""

import time
import requests
from typing import Dict, Any, List, Optional, Tuple, Callable
from loguru import logger
from .binance_websocket import get_binance_websocket, start_binance_websocket

class BinanceAPI:
    """Binance API client for real-time volume data and historical candles"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.websocket = None
        self.last_volume_data = None
        self.base_url = "https://api.binance.com/api/v3"
        
        logger.info("📊 Binance API Client initialized for real-time volume data")
    
    def get_real_time_volume(self) -> Dict[str, Any]:
        """
        Get real-time volume data from Binance WebSocket
        
        Returns:
            Dict with real-time volume data for scalping
        """
        try:
            # Ensure WebSocket is running
            if not self.websocket or not self.websocket.is_connected():
                self.websocket = start_binance_websocket(self.symbol)
                time.sleep(1)  # Give WebSocket time to connect
            
            # Get volume data from WebSocket
            if self.websocket and self.websocket.is_connected():
                volume_data = self.websocket.get_volume_data()
                
                # Add additional scalping-specific data
                volume_data.update({
                    "data_source": "binance_websocket",
                    "symbol": self.symbol,
                    "real_time": True,
                    "scalping_ready": True
                })
                
                self.last_volume_data = volume_data
                return volume_data
            else:
                # Fallback to cached data if WebSocket not available
                if self.last_volume_data:
                    logger.warning("⚠️ Using cached Binance volume data (WebSocket disconnected)")
                    return self.last_volume_data
                else:
                    raise ValueError("No Binance volume data available - NO FALLBACKS")
                    
        except Exception as e:
            logger.error(f"❌ Failed to get Binance volume data: {e}")
            raise ValueError(f"Binance volume data fetch failed - NO FALLBACKS: {e}")
    
    # _get_fallback_volume_data method removed - NO FALLBACKS policy
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket and self.websocket.is_connected()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status"""
        if self.websocket:
            volume_data = self.websocket.get_volume_data()
            return {
                "connected": self.websocket.is_connected(),
                "connection_status": volume_data.get("connection_status", "unknown"),
                "last_update": volume_data.get("timestamp", 0),
                "symbol": self.symbol
            }
        else:
            return {
                "connected": False,
                "connection_status": "not_initialized",
                "last_update": 0,
                "symbol": self.symbol
            }
    
    def get_historical_klines(self, symbol: str, interval: str, start_time: int = None, end_time: int = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get historical klines (candles) from Binance REST API
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Kline interval (e.g., "5m", "1h", "1d")
            start_time: Start time in milliseconds (optional)
            end_time: End time in milliseconds (optional)
            limit: Maximum number of klines to retrieve (default: 1000, max: 1000)
            
        Returns:
            List of candle dictionaries with timestamp, open, high, low, close, volume, trades_count
        """
        try:
            url = f"{self.base_url}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000)  # Binance max limit is 1000
            }
            
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            klines_data = response.json()
            
            # Convert Binance kline format to our candle format
            # Binance format: [openTime, open, high, low, close, volume, closeTime, quoteVolume, trades, ...]
            candles = []
            for kline in klines_data:
                candle = {
                    "timestamp": kline[0] / 1000.0,  # Convert ms to seconds
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "trades_count": int(kline[8]) if len(kline) > 8 else 0
                }
                candles.append(candle)
            
            return candles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch historical klines from Binance: {e}")
            raise ValueError(f"Binance historical klines fetch failed: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing Binance klines: {e}")
            raise ValueError(f"Binance klines processing failed: {e}")


# Singleton pattern implementation
_global_binance_api = None

def get_global_binance_api() -> BinanceAPI:
    """Get the global BinanceAPI singleton instance"""
    global _global_binance_api
    if _global_binance_api is None:
        _global_binance_api = BinanceAPI("BTCUSDT")
    return _global_binance_api

# Backward compatibility
binance_api = get_global_binance_api()
