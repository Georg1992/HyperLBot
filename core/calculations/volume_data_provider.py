#!/usr/bin/env python3
"""
Volume Data Provider - Clean implementation
Handles data fetching for volume calculations
"""

import time
from typing import Dict, List, Any
from loguru import logger


class VolumeDataProvider:
    """Data provider for volume calculations"""
    
    def __init__(self, symbol: str = "BTC"):
        self.symbol = symbol
        logger.debug(f"VolumeDataProvider initialized for {symbol}")
    
    def fetch_raw_trades(self) -> List[Dict[str, Any]]:
        """Fetch raw trade data - placeholder implementation"""
        # This would integrate with the actual data source
        return []
    
    def fetch_hyperliquid_volume_data(self, websocket) -> Dict[str, Any]:
        """Fetch volume data from Hyperliquid WebSocket"""
        if not websocket:
            return {"raw_trades": []}
        
        try:
            raw_trades = websocket.get_raw_trades()
            return {"raw_trades": raw_trades}
        except Exception as e:
            logger.error(f"❌ Failed to fetch volume data: {e}")
            return {"raw_trades": []}
    
    def calculate_5m_volume(self, raw_trades: List[Dict], current_time: float) -> Dict[str, Any]:
        """
        Calculate 5m volume from raw trades - aligned with exact candle boundaries
        
        Volume resets at exact 5-minute boundaries (00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
        to match candle boundaries for consistency.
        """
        try:
            # Get exact 5-minute candle start time (aligned with candle boundaries)
            from core.utils.time_utils import TimeUtils
            candle_start_timestamp = TimeUtils.get_5m_candle_start_time(current_time)
            
            # Filter trades within current 5-minute candle (from candle start to now)
            recent_trades = [
                trade for trade in raw_trades
                if trade.get('timestamp', 0) >= candle_start_timestamp
            ]
            
            # Calculate total volume for current candle
            total_volume = sum(trade.get('size', 0) for trade in recent_trades)
            
            return {
                "current_5m_volume": total_volume,
                "trade_count": len(recent_trades),
                "reset_time": candle_start_timestamp,  # Exact candle boundary timestamp
                "time_window": "5m",
                "candle_start": candle_start_timestamp  # For debugging/verification
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate 5m volume: {e}")
            return {"current_5m_volume": 0.0, "trade_count": 0}
    
    def get_volume_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get volume history - placeholder implementation"""
        return []
