#!/usr/bin/env python3
"""
Orderbook Data Fetcher Module
Fetches orderbook data from Hyperliquid API (pure data fetching, no analysis)
"""

import time
import statistics
from typing import Dict, Any, List
from loguru import logger
from core.constants import volume_constants, technical_constants

class OrderbookDataFetcher:
    """Fetches orderbook data from Hyperliquid API (pure data fetching, no analysis)"""
    
    def __init__(self, api_instance):
        """Initialize with reference to main API instance"""
        self.api = api_instance
    
    # get_volume_analysis() REMOVED - Volume logic moved to VolumeCalculator for clean architecture
    # MarketDataManager now handles volume analysis using VolumeCalculator delegation

    # get_volatility_analysis() removed - 167 lines of Hyperliquid orderbook volatility logic eliminated
    # Using Yahoo Finance 5-minute candle volatility instead (aligned with 5m trading strategy)

    # get_pressure() REMOVED - Pressure logic moved to PressureCalculator for clean architecture
    # MarketDataManager now handles pressure analysis using PressureCalculator delegation

    def get_orderbook(self, symbol: str = None) -> Dict[str, Any]:
        """Get order book data from API"""
        try:
            symbol = symbol or self.api.config.SYMBOL
            # Use the API's get_orderbook method directly
            if hasattr(self.api, 'get_orderbook'):
                return self.api.get_orderbook(symbol)
            else:
                # Fallback: return None if method doesn't exist
                logger.warning(f"⚠️ API does not have get_orderbook method")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook: {e}")
            return None

    # _get_default_pressure() REMOVED - Pressure logic moved to PressureCalculator
    # _calculate_pressure_metrics() REMOVED - Dummy implementation eliminated
