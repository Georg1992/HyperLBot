#!/usr/bin/env python3
"""
Binance API Client
Provides real-time volume data via WebSocket for scalping strategies
"""

import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from loguru import logger
from .binance_websocket import get_binance_websocket, start_binance_websocket

class BinanceAPI:
    """Binance API client for real-time volume data"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.websocket = None
        self.last_volume_data = None
        
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
