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
        """Fetch volume data from Hyperliquid WebSocket - NO FALLBACKS"""
        if not websocket:
            raise ValueError("Hyperliquid WebSocket not available for volume data - NO FALLBACKS")
        
        try:
            raw_trades = websocket.get_raw_trades()
            return {"raw_trades": raw_trades}
        except Exception as e:
            logger.error(f"❌ Failed to fetch volume data: {e}")
            raise
    
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
                if ('timestamp' in trade and trade['timestamp'] >= candle_start_timestamp)
            ]
            
            # Calculate total volume for current candle
            total_volume = sum(trade.get('size', 0) for trade in recent_trades)
            
            return {
                "current_5m_volume": total_volume,  # Can be 0.0 if no trades (valid result)
                "trade_count": len(recent_trades),  # Can be 0 if no trades (valid result)
                "reset_time": candle_start_timestamp,  # Exact candle boundary timestamp
                "time_window": "5m",
                "candle_start": candle_start_timestamp  # For debugging/verification
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate 5m volume: {e}")
            raise  # NO FALLBACKS - calculation failure should raise, not return 0.0
    
    def get_volume_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get volume history from database for percentile-based categorization
        
        Fetches last 7 days of completed candles (~2016 candles) for statistically
        significant percentile calculation. This is a solid implementation with no fallbacks.
        
        Args:
            count: Parameter kept for compatibility, but uses 2016 candles for proper statistics
            
        Returns:
            List of volume dictionaries with timestamp and volume
            
        Raises:
            ValueError: If database is unavailable or insufficient data exists
        """
        from core.services.historical_data_service import get_global_historical_data_service
        historical_service = get_global_historical_data_service()
        
        if not historical_service:
            raise ValueError("Historical data service not available for volume history")
        
        if not historical_service._candle_storage:
            raise ValueError("Candle storage not available for volume history")
        
        # Fetch last 7 days of candles (7 days * 288 candles/day = 2016 candles)
        # This provides a statistically significant sample for percentile calculation
        candles = historical_service._candle_storage.get_candles_by_count(2016)
        
        if not candles:
            raise ValueError("No candles available in database for volume history")
        
        if len(candles) < 20:
            raise ValueError(f"Insufficient candles in database: {len(candles)} (minimum 20 required for percentile calculation)")
        
        # Extract volume data (only include candles with valid volume > 0)
        volume_history = [
            {
                "volume": candle["volume"] if "volume" in candle else 0.0,
                "timestamp": candle["timestamp"] if "timestamp" in candle else 0.0
            }
            for candle in candles
            if ("volume" in candle and candle["volume"] > 0)
        ]
        
        if len(volume_history) < 20:
            raise ValueError(f"Insufficient valid volume records: {len(volume_history)} (minimum 20 required)")
        
        logger.debug(f"📊 Fetched {len(volume_history)} volume records from database for percentile calculation")
        return volume_history
