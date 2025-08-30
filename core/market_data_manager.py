#!/usr/bin/env python3
"""
Centralized Market Data Manager
Eliminates redundant calculations and provides single source of truth for all market data
"""

import time
import statistics
from typing import Dict, List, Any, Optional
from loguru import logger
from core.analysis.real_time.volatility_calculator import VolatilityCalculator

class MarketDataManager:
    """Centralized market data manager to eliminate redundant calculations"""
    
    def __init__(self):
        # Cache for market data to avoid redundant API calls
        self._market_data_cache = {}
        self._cache_timestamps = {}
        self._cache_duration = 5  # 5 seconds cache for real-time data
        
        # Cache for calculated indicators
        self._indicator_cache = {}
        self._indicator_timestamps = {}
        self._indicator_cache_duration = 60  # 1 minute for calculated indicators
        
        # Initialize volatility calculator
        self.volatility_calculator = VolatilityCalculator()
        
        logger.info("📊 Market Data Manager initialized - Centralized data management")
    
    def _get_cached_data(self, key: str, cache_duration: int) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self._market_data_cache:
            timestamp = self._cache_timestamps.get(key, 0)
            if time.time() - timestamp < cache_duration:
                return self._market_data_cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict, cache_duration: int):
        """Cache data with timestamp"""
        self._market_data_cache[key] = data
        self._cache_timestamps[key] = time.time()
    
    def get_hyperliquid_data(self, hyperliquid_api, symbol: str = "BTC") -> Dict[str, Any]:
        """Get all Hyperliquid data with caching to avoid redundant API calls"""
        # Check if hyperliquid_api is None - show explicit error instead of crashing
        if hyperliquid_api is None:
            logger.error(f"❌ HyperliquidAPI is None - cannot fetch data for {symbol}")
            return {
                "volume_data": {},
                "volatility_data": {},
                "ultimate_pressure_data": {},
                "current_price": None,
                "timestamp": time.time(),
                "error": "HyperliquidAPI not initialized"
            }
        
        cache_key = f"hyperliquid_{symbol}"
        cached_data = self._get_cached_data(cache_key, self._cache_duration)
        
        if cached_data:
            return cached_data
        
        try:
            # Fetch all Hyperliquid data in one call
            volume_data = hyperliquid_api.get_volume_analysis(symbol)
            volatility_data = hyperliquid_api.get_volatility_analysis(symbol)
            ultimate_pressure_data = hyperliquid_api.get_ultimate_pressure(symbol)
            current_price = hyperliquid_api.get_current_price(symbol)
            
            data = {
                "volume_data": volume_data or {},
                "volatility_data": volatility_data or {},
                "ultimate_pressure_data": ultimate_pressure_data or {},
                "current_price": current_price,
                "timestamp": time.time()
            }
            
            self._cache_data(cache_key, data, self._cache_duration)
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to get Hyperliquid data: {e}")
            return {
                "volume_data": {},
                "volatility_data": {},
                "ultimate_pressure_data": {},
                "current_price": None,
                "timestamp": time.time()
            }
    
    def calculate_trend(self, candles: List[Dict], periods: int = 5) -> Dict[str, Any]:
        """Use trend manager for advanced trend calculation"""
        from core.analysis.trend_manager import trend_manager
        return trend_manager.calculate_trend(candles, periods)
    
    def calculate_volatility(self, candles: List[Dict], periods: int = 20) -> float:
        """Centralized volatility calculation using VolatilityCalculator"""
        cache_key = f"volatility_{periods}_{hash(str(candles[-periods:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < periods:
                return 0.0
            
            # Use the centralized volatility calculator
            result = self.volatility_calculator.calculate_candle_volatility(candles[-periods:], "5m")
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation failed: {e}")
            return 0.0
    
    def calculate_support_resistance(self, candles: List[Dict], lookback: int = 20) -> Dict[str, float]:
        """Centralized support/resistance calculation to eliminate redundant calculations"""
        cache_key = f"support_resistance_{lookback}_{hash(str(candles[-lookback:]))}"
        cached_result = self._get_cached_data(cache_key, self._indicator_cache_duration)
        
        if cached_result:
            return cached_result
        
        try:
            if len(candles) < lookback:
                return {"support": 0.0, "resistance": 0.0}
            
            recent_candles = candles[-lookback:]
            highs = [candle["high"] for candle in recent_candles]
            lows = [candle["low"] for candle in recent_candles]
            
            resistance = max(highs)
            support = min(lows)
            
            result = {
                "support": round(support, 2),
                "resistance": round(resistance, 2)
            }
            
            self._cache_data(cache_key, result, self._indicator_cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"❌ Support/resistance calculation failed: {e}")
            return {"support": 0.0, "resistance": 0.0}
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get simplified cache status for monitoring"""
        return {
            "market_data_entries": len(self._market_data_cache),
            "indicator_entries": len(self._indicator_cache),
            "total_entries": len(self._market_data_cache) + len(self._indicator_cache),
            "cache_age_range": f"{min(time.time() - t for t in self._cache_timestamps.values()):.1f}-{max(time.time() - t for t in self._cache_timestamps.values()):.1f}s" if self._cache_timestamps else "empty"
        }

# Global instance
market_data_manager = MarketDataManager()
