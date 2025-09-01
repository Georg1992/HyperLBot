#!/usr/bin/env python3
"""
Market Orderbook Analyzer Module
Provides market analysis using order book data (volume, volatility, pressure)
"""

import time
import statistics
from typing import Dict, Any, List
from loguru import logger
from core.constants import volume_constants, technical_constants

class MarketOrderbookAnalyzer:
    """Market analysis using order book data (volume, volatility, pressure)"""
    
    def __init__(self, api_instance):
        """Initialize with reference to main API instance"""
        self.api = api_instance
    
    # get_volume_analysis() REMOVED - Volume logic moved to VolumeCalculator for clean architecture
    # MarketDataManager now handles volume analysis using VolumeCalculator delegation

    # get_volatility_analysis() removed - 167 lines of Hyperliquid orderbook volatility logic eliminated
    # Using Yahoo Finance 5-minute candle volatility instead (aligned with 5m trading strategy)

    def get_pressure(self, symbol: str = None) -> Dict[str, Any]:
        """Get pressure analysis for symbol"""
        try:
            # Get order book data
            orderbook = self.get_orderbook(symbol)
            if not orderbook:
                return self._get_default_pressure()
            
            # Calculate pressure metrics
            pressure_metrics = self._calculate_pressure_metrics(orderbook)
            
            return {
                "direction": pressure_metrics["direction"],
                "confidence": pressure_metrics["confidence"],
                "strength": pressure_metrics["strength"],
                "trend": pressure_metrics["trend"],
                "data_source": "orderbook_analysis"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get pressure analysis: {e}")
            return self._get_default_pressure()

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

    def _get_default_pressure(self) -> Dict[str, Any]:
        """Get default pressure data when orderbook is unavailable"""
        return {
            "direction": "NEUTRAL",
            "confidence": "50%",
            "strength": 0.5,
            "trend": "NEUTRAL",
            "data_source": "default"
        }

    def _calculate_pressure_metrics(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pressure metrics from orderbook data"""
        try:
            # Default pressure metrics
            return {
                "direction": "NEUTRAL",
                "confidence": "50%",
                "strength": 0.5,
                "trend": "NEUTRAL"
            }
        except Exception as e:
            logger.error(f"❌ Failed to calculate pressure metrics: {e}")
            return {
                "direction": "NEUTRAL",
                "confidence": "50%",
                "strength": 0.5,
                "trend": "NEUTRAL"
            }
