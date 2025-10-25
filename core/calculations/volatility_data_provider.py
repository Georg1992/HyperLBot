#!/usr/bin/env python3
"""
Volatility Data Provider Module
Provides candle data and basic volatility calculations for the VolatilityCalculator
"""

import time
from typing import Dict, List, Any, Tuple
from loguru import logger


class VolatilityDataProvider:
    """
    Provides candle data and basic volatility calculations.
    Encapsulates data access and basic data processing for volatility analysis.
    """
    
    def __init__(self, symbol: str = "BTC"):
        self.symbol = symbol
        from core.services.historical_data_service import create_historical_data_service
        self.historical_service = create_historical_data_service()
        logger.debug(f"📊 VolatilityDataProvider initialized for {symbol}")
    
    def fetch_candle_data(self, timeframe: str = "5m", count: int = 30) -> List[Dict]:
        """
        Fetch candle data for volatility calculation.
        
        Args:
            timeframe: Timeframe for candles (default: "5m")
            count: Number of candles to fetch (default: 30)
        
        Returns:
            List of candle dictionaries
        """
        try:
            logger.debug(f"Fetching {count} {timeframe} candles for {self.symbol}...")
            
            if timeframe == "5m":
                candles = self.historical_service.get_5m_candles(self.symbol, count)
            else:
                candles = self.historical_service.get_historical_candles(self.symbol, timeframe, count)
            
            if not candles or len(candles) < 1:
                raise ValueError(f"Insufficient {timeframe} candles: {len(candles) if candles else 0}")
            
            logger.debug(f"📊 Retrieved {len(candles)} {timeframe} candles for {self.symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch candle data for {self.symbol}: {e}")
            raise ValueError(f"Data fetching failed: {e}")
    
    def calculate_basic_volatility(self, candles: List[Dict], period_minutes: int = 15) -> Dict[str, Any]:
        """
        Calculate basic volatility metrics from candle data.
        
        Args:
            candles: List of candle dictionaries
            period_minutes: Analysis period in minutes
        
        Returns:
            Dictionary with basic volatility metrics
        """
        try:
            if len(candles) < 1:
                return {"volatility": 0.0, "range": 0.0, "avg_price": 0.0}
            
            # Use the most recent candles for the calculated period
            period_candles = max(1, period_minutes // 5)  # Convert minutes to 5m candles
            recent_candles = candles[-period_candles:] if len(candles) >= period_candles else candles
            
            # Calculate price range and average
            all_highs = [candle["high"] for candle in recent_candles if candle["high"] > 0]
            all_lows = [candle["low"] for candle in recent_candles if candle["low"] > 0]
            all_closes = [candle["close"] for candle in recent_candles if candle["close"] > 0]
            
            if not all_highs or not all_lows or not all_closes:
                return {"volatility": 0.0, "range": 0.0, "avg_price": 0.0}
            
            max_high = max(all_highs)
            min_low = min(all_lows)
            total_range = max_high - min_low
            avg_price = sum(all_closes) / len(all_closes)
            
            # Basic volatility as range percentage
            basic_volatility = total_range / avg_price if avg_price > 0 else 0.0
            
            return {
                "volatility": basic_volatility,
                "range": total_range,
                "avg_price": avg_price,
                "max_high": max_high,
                "min_low": min_low,
                "candle_count": len(recent_candles)
            }
            
        except Exception as e:
            logger.error(f"❌ Basic volatility calculation failed: {e}")
            return {"volatility": 0.0, "range": 0.0, "avg_price": 0.0}
    
    def invalidate_cache(self):
        """Invalidate any cached data"""
        try:
            # Clear any cached candle data
            from core.services.centralized_cache import get_global_centralized_cache
            cache = get_global_centralized_cache()
            cache.invalidate_pattern("historical_candles_*")
            logger.debug("📊 VolatilityDataProvider cache invalidated")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate cache: {e}")
