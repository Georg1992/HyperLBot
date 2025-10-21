#!/usr/bin/env python3
"""
Chart Data Service
Handles chart data preparation and ongoing candle creation
Single Responsibility: Chart data management for dashboard
"""

import time
import datetime as dt
from typing import Dict, Any, List, Optional
from loguru import logger


class ChartDataService:
    """Dedicated service for chart data preparation and management"""
    
    def __init__(self):
        logger.info("📊 Chart Data Service initialized")
    
    def prepare_chart_data(self, current_price: float, market_data_service, 
                          pattern_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prepare complete chart data structure for dashboard
        
        Args:
            current_price: Current market price
            market_data_service: Service to fetch historical candles
            pattern_analysis: Pattern analysis data to include
            
        Returns:
            Dict with chart data structure
        """
        try:
            # Get the current 5m candle start time (UTC synchronized)
            candle_start_timestamp = self._get_5m_candle_start_time()
            
            # ChartDataService fetches its own candles (single responsibility)
            chart_candles_5m = market_data_service.get_historical_candles("BTC", "5m", 20)
            
            # NO FALLBACKS - Must have candles
            if not chart_candles_5m or len(chart_candles_5m) == 0:
                logger.error("❌ NO CANDLES AVAILABLE - NO FALLBACKS")
                return {}
            
            # Get real-time volume from the last candle if available
            real_time_volume = 0.0
            if chart_candles_5m and len(chart_candles_5m) > 0:
                real_time_volume = chart_candles_5m[-1].get("volume", 0.0)
            
            # NO FALLBACKS - Use exactly the candles provided
            # Remove the last candle if it's the current ongoing one (same timestamp as our ongoing candle)
            if len(chart_candles_5m) > 0:
                last_candle_timestamp = chart_candles_5m[-1]["timestamp"]
                if abs(last_candle_timestamp - candle_start_timestamp) < 300:  # Within 5 minutes
                    chart_candles_5m = chart_candles_5m[:-1]  # Remove the ongoing candle from historical data
            
            logger.debug(f"📊 Chart data prepared using fetched candles: {len(chart_candles_5m)} historical")
            
            # Create ongoing candle using utility method
            ongoing_candle = self._create_ongoing_candle(
                current_price, chart_candles_5m, real_time_volume, candle_start_timestamp
            )
            
            # Create exactly 20 candles: 19 historical + 1 ongoing
            chart_candles_with_ongoing = chart_candles_5m.copy()
            chart_candles_with_ongoing.append(ongoing_candle)
            
            # Prepare chart data structure
            return {
                "historical": chart_candles_with_ongoing,  # Include ongoing candle in historical array
                "ongoing": ongoing_candle,  # Keep separate for reference
                "predicted": [],
                "pattern_analysis": pattern_analysis or {}
            }
            
        except Exception as e:
            logger.error(f"❌ Chart data preparation failed: {e}")
            return {}
    
    def _get_5m_candle_start_time(self) -> float:
        """
        Get the current 5-minute candle start time (UTC synchronized)
        
        Returns:
            Timestamp of current 5m candle start
        """
        from core.utils.time_utils import get_5m_candle_start_time
        return get_5m_candle_start_time()
    
    def _create_ongoing_candle(self, current_price: float, chart_candles_5m: List[Dict], 
                              real_time_volume: float, candle_start_timestamp: float) -> Dict[str, Any]:
        """
        Create ongoing candle structure with current price
        
        Args:
            current_price: Current market price
            chart_candles_5m: Historical 5m candles for reference
            real_time_volume: Current 5m candle volume
            candle_start_timestamp: Timestamp of candle start
            
        Returns:
            Dict with ongoing candle data
        """
        current_time = time.time()
        
        return {
            "open": chart_candles_5m[-1]["close"] if chart_candles_5m else current_price,
            "close": current_price,
            "high": max(chart_candles_5m[-1]["close"] if chart_candles_5m else current_price, current_price),
            "low": min(chart_candles_5m[-1]["close"] if chart_candles_5m else current_price, current_price),
            "volume": real_time_volume if real_time_volume > 0 else (chart_candles_5m[-1]["volume"] if chart_candles_5m else 0),
            "timestamp": candle_start_timestamp,
            "is_ongoing": True,
            "trades_count": 0,
            "last_trade_time": current_time
        }


# Singleton pattern implementation
_global_chart_data_service = None

def get_global_chart_data_service() -> ChartDataService:
    """Get the global ChartDataService singleton instance"""
    global _global_chart_data_service
    if _global_chart_data_service is None:
        _global_chart_data_service = ChartDataService()
    return _global_chart_data_service
